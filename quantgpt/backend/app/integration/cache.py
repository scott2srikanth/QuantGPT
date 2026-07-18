"""In-memory TTL cache for the Integration Layer.

Used by adapters to cache market data responses (quotes, option chains,
instruments) that are expensive to fetch and tolerate short staleness.
Redis-backed caching can be layered in later without changing call sites.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from app.logging.config import get_logger

_log = get_logger("app.integration.cache")


class TTLCache:
    """Simple thread-safe-ish in-memory TTL cache.

    Not a full LRU — entries expire by time. Adequate for short-TTL
    market-data caching (seconds). For longer TTLs or cross-process
    sharing, swap the implementation for Redis without changing callers.
    """

    def __init__(self, default_ttl: int = 30) -> None:
        self.default_ttl = default_ttl
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    def get_or_set(self, key: str, factory: Callable[[], Any], ttl: int | None = None) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = factory()
        self.set(key, value, ttl)
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        t = ttl if ttl is not None else self.default_ttl
        self._store[key] = (time.monotonic() + t, value)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def size(self) -> int:
        return len(self._store)
