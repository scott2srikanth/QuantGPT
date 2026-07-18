"""Redis-backed background worker placeholder.

No work is performed yet — this exists so the wiring (Redis client, worker loop)
is in place and can be filled in later without touching the rest of the app.
"""

from __future__ import annotations

import redis

from app.config.settings import get_settings
from app.logging.config import get_logger

_log = get_logger("app.workers.redis")
_settings = get_settings()


def get_redis() -> redis.Redis:
    return redis.from_url(_settings.redis_url, decode_responses=True)


def worker_loop() -> None:
    """Stub worker loop — no-op for now."""
    _log.info("worker.start", redis=_settings.redis_url)
    client = get_redis()
    _log.info("worker.redis_ping", ok=client.ping())
    _log.info("worker.idle")
