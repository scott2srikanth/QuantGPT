"""Request correlation, rate limiting, metrics and tamper-evident audit entries."""

from __future__ import annotations

import hashlib
import time
import uuid
from collections import defaultdict, deque

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.settings import get_settings
from app.db.session import SessionLocal
from app.logging.config import get_logger
from app.models.models import AuditLog
from app.observability.metrics import HTTP_DURATION, HTTP_ERRORS, HTTP_REQUESTS

_windows: dict[str, deque[float]] = defaultdict(deque)
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_EXCLUDED_AUDIT_PATHS = {"/api/v1/health", "/api/v1/health/ready", "/metrics"}


def _route_path(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", None) or request.url.path


class ProductionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        settings = get_settings()
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:128]
        client_ip = request.client.host if request.client else "unknown"
        is_auth = request.url.path.startswith("/api/v1/auth/")
        allowance = settings.rate_limit_auth_requests if is_auth else settings.rate_limit_requests
        key = f"{client_ip}:{'auth' if is_auth else 'api'}"
        now = time.monotonic()
        window = _windows[key]
        while window and window[0] <= now - settings.rate_limit_window_seconds:
            window.popleft()
        if len(window) >= allowance:
            return JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded", "request_id": request_id},
                headers={"Retry-After": str(settings.rate_limit_window_seconds), "X-Request-ID": request_id},
            )
        window.append(now)
        started = time.perf_counter()
        structlog.contextvars.bind_contextvars(request_id=request_id, method=request.method, path=request.url.path)
        try:
            response = await call_next(request)
        except Exception:
            path = _route_path(request)
            HTTP_ERRORS.labels(request.method, path).inc()
            get_logger("app.request").exception("request.failed")
            raise
        finally:
            structlog.contextvars.clear_contextvars()
        duration = time.perf_counter() - started
        path = _route_path(request)
        HTTP_REQUESTS.labels(request.method, path, response.status_code).inc()
        HTTP_DURATION.labels(request.method, path).observe(duration)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        get_logger("app.request").info("request.complete", status_code=response.status_code, duration_ms=round(duration * 1000, 2))
        if settings.audit_log_enabled and request.method in _MUTATING_METHODS and request.url.path not in _EXCLUDED_AUDIT_PATHS:
            self._write_audit(request, response.status_code, request_id, client_ip)
        return response

    @staticmethod
    def _write_audit(request: Request, status_code: int, request_id: str, client_ip: str) -> None:
        """Store metadata only; never persist request bodies, credentials or bearer tokens."""
        try:
            session = SessionLocal()
            session.add(AuditLog(
                request_id=request_id,
                action=f"{request.method} {_route_path(request)}",
                status_code=status_code,
                ip_hash=hashlib.sha256(client_ip.encode()).hexdigest(),
                user_agent=(request.headers.get("user-agent") or "")[:512],
            ))
            session.commit()
            session.close()
        except Exception:
            get_logger("app.audit").exception("audit.write_failed", request_id=request_id)
