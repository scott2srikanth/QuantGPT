"""Base OpenAlgo adapter.

All OpenAlgo adapters share the same HTTP transport, API key, cache, and
logging. This base wires them up once so concrete adapters only implement
the capability-specific translation between OpenAlgo's JSON and QuantGPT's
neutral models.

OpenAlgo REST conventions used here:
  - All endpoints live under /api/v1
  - The API key is sent in the JSON body as `apikey` (not a header)
  - Responses are JSON with a `status` field ("success" / "error") and `data`
"""

from __future__ import annotations

from typing import Any

from app.integration.cache import TTLCache
from app.integration.exceptions import (
    AdapterNotImplementedError,
    BackendServerError,
    BackendValidationError,
)
from app.integration.http_transport import HttpTransport
from app.logging.config import get_logger


class BaseOpenAlgoAdapter:
    """Shared transport + helpers for OpenAlgo adapters."""

    def __init__(
        self,
        *,
        transport: HttpTransport,
        api_key: str,
        cache: TTLCache,
        cache_ttl: int = 30,
    ) -> None:
        self._http = transport
        self._api_key = api_key
        self._cache = cache
        self._cache_ttl = cache_ttl
        self._log = get_logger(f"app.integration.{self.__class__.__name__}")

    # ── HTTP helpers ──
    def _post(self, path: str, body: dict[str, Any] | None = None) -> Any:
        payload = {"apikey": self._api_key, **(body or {})}
        resp = self._http.post(path, json=payload)
        return self._unwrap(resp, path)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        params = {"apikey": self._api_key, **(params or {})}
        resp = self._http.get(path, params=params)
        return self._unwrap(resp, path)

    @staticmethod
    def _unwrap(resp: dict[str, Any], path: str) -> Any:
        status = resp.get("status")
        if status == "success":
            return resp.get("data")
        if status == "error":
            msg = resp.get("message", "unknown error")
            raise BackendValidationError(f"{path}: {msg}")
        # Some endpoints return raw data without a status envelope
        if "data" in resp:
            return resp["data"]
        return resp

    # ── cache helpers ──
    def _cached(self, key: str, factory: Any) -> Any:
        return self._cache.get_or_set(key, factory, ttl=self._cache_ttl)

    # ── not-implemented stub (for capabilities OpenAlgo lacks) ──
    @staticmethod
    def _not_implemented(capability: str) -> None:
        raise AdapterNotImplementedError(f"OpenAlgo adapter does not implement: {capability}")
