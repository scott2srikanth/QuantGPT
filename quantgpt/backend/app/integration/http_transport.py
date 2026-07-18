"""HTTP transport with connection pooling, retry, and structured logging.

Adapters use this instead of raw httpx so pooling, retry, and error
translation are consistent across all adapters and backends.
"""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.integration.exceptions import (
    BackendAuthError,
    BackendNotFoundError,
    BackendRateLimitError,
    BackendServerError,
    BackendTimeoutError,
    BackendUnreachableError,
    BackendValidationError,
)
from app.logging.config import get_logger

_log = get_logger("app.integration.http")


class HttpTransport:
    """Pooled HTTP client with retry + backend-neutral error translation.

    A single httpx.Client is reused across all requests (connection pooling).
    Retry handles transient network errors and 429/5xx responses with
    exponential backoff. Non-retryable errors (4xx except 429) are translated
    to IntegrationError subclasses immediately.
    """

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 10.0,
        max_retries: int = 3,
        default_headers: dict[str, str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Content-Type": "application/json", **(default_headers or {})},
            http2=False,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )

    # ── lifecycle ──
    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HttpTransport":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # ── public ──
    def post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("POST", path, json=json)

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("GET", path, params=params)

    # ── internal ──
    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        @retry(
            retry=retry_if_exception_type(
                (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout, BackendRateLimitError, BackendServerError)
            ),
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=0.5, max=5),
            reraise=True,
        )
        def _do() -> dict[str, Any]:
            _log.debug("http.request", method=method, path=path)
            try:
                r = self._client.request(method, path, **kwargs)
            except httpx.ConnectError as e:
                raise BackendUnreachableError(str(e)) from e
            except httpx.TimeoutException as e:
                raise BackendTimeoutError(str(e)) from e

            self._raise_for_status(r, path)
            return self._parse(r, path)

        return _do()

    @staticmethod
    def _raise_for_status(r: httpx.Response, path: str) -> None:
        code = r.status_code
        if code < 400:
            return
        body = r.text[:500]
        if code == 401 or code == 403:
            raise BackendAuthError(f"{path} -> {code}: {body}")
        if code == 404:
            raise BackendNotFoundError(f"{path} -> {code}: {body}")
        if code == 429:
            raise BackendRateLimitError(f"{path} -> 429: {body}")
        if 400 <= code < 500:
            raise BackendValidationError(f"{path} -> {code}: {body}")
        raise BackendServerError(f"{path} -> {code}: {body}")

    @staticmethod
    def _parse(r: httpx.Response, path: str) -> dict[str, Any]:
        try:
            return r.json()
        except Exception as e:
            raise BackendServerError(f"{path}: invalid JSON: {e}") from e
