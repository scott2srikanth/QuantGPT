"""OpenAlgo Integration Layer.

This is the ONLY module permitted to talk to OpenAlgo. The rest of QuantGPT
depends on this client, never on OpenAlgo directly. OpenAlgo itself is never
modified — QuantGPT is an external client of its REST /api/v1 and WS proxy.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.logging.config import get_logger

_log = get_logger("app.integration.openalgo")


class OpenAlgoError(Exception):
    """Raised when OpenAlgo returns an error or is unreachable."""


class OpenAlgoClient:
    """Synchronous REST client wrapper around OpenAlgo /api/v1.

    No trading logic here — this is a thin transport. Higher-level helpers
    (quotes, positions, order placement) will be added in later phases.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        websocket_url: str,
        timeout: float = 10.0,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.websocket_url = websocket_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.Client | None = None

    # ── lifecycle ──
    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    # ── public helpers ──
    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def status(self) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "api_key_configured": self.is_configured,
            "websocket_url": self.websocket_url,
        }

    def ping(self) -> bool:
        """Best-effort reachability check against OpenAlgo /api/v1/ping."""
        try:
            resp = self._post("/api/v1/ping", {"apikey": self.api_key or "missing"})
            return resp.get("status") == "success"
        except Exception:
            return False

    # ── low-level ──
    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=5),
        reraise=True,
    )
    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        client = self._get_client()
        try:
            r = client.post(path, json=body)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            _log.error("openalgo.http_status", path=path, status=e.response.status_code)
            raise OpenAlgoError(f"OpenAlgo {path} returned {e.response.status_code}") from e
        except httpx.HTTPError as e:
            _log.error("openalgo.http_error", path=path, error=str(e))
            raise


class OpenAlgoWSClient:
    """Placeholder for the OpenAlgo WebSocket proxy client (port 8765).

    Not yet implemented — no trading logic in this phase. The class exists
    so downstream modules can depend on the interface and we can wire it in
    without touching the rest of the codebase.
    """

    def __init__(self, *, websocket_url: str, api_key: str) -> None:
        self.websocket_url = websocket_url
        self.api_key = api_key
        self._task: asyncio.Task | None = None

    async def connect(self) -> None:
        _log.info("openalgo.ws.connect_stub", url=self.websocket_url)

    async def close(self) -> None:
        _log.info("openalgo.ws.close_stub")
