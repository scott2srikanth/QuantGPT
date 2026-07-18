"""Shared test fixtures for the Integration Layer + Agent Framework.

Provides:
  - FakeHttp: a canned-response HTTP transport for adapter tests
  - db: an in-memory SQLite session for persistence-backed tests
"""

from __future__ import annotations

from typing import Any, Callable

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.integration.cache import TTLCache
from app.integration.adapters.base import BaseOpenAlgoAdapter
from app.models import models  # noqa: F401 — ensure all tables are registered


class FakeHttp:
    """Stand-in for HttpTransport. Returns canned responses by (method, path)."""

    def __init__(self) -> None:
        self.base_url = "http://openalgo.test"
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self._routes: dict[tuple[str, str], Callable[[dict[str, Any]], dict[str, Any]]] = {}

    def route(self, method: str, path: str, handler: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        self._routes[(method, path)] = handler

    def set_response(self, method: str, path: str, response: dict[str, Any]) -> None:
        self._routes[(method, path)] = lambda _body: response

    def post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        self.calls.append(("POST", path, json or {}))
        h = self._routes.get(("POST", path))
        if h is None:
            raise AssertionError(f"unexpected POST {path}")
        return h(json or {})

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.calls.append(("GET", path, params or {}))
        h = self._routes.get(("GET", path))
        if h is None:
            raise AssertionError(f"unexpected GET {path}")
        return h(params or {})

    def close(self) -> None:
        pass


@pytest.fixture
def fake_http() -> FakeHttp:
    return FakeHttp()


@pytest.fixture
def cache() -> TTLCache:
    return TTLCache(default_ttl=0)


def make_adapter(cls: type[BaseOpenAlgoAdapter], fake_http: FakeHttp, cache: TTLCache, api_key: str = "test-key", ttl: int = 0) -> Any:
    return cls(transport=fake_http, api_key=api_key, cache=cache, cache_ttl=ttl)


# ── Agent framework fixtures ──
@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def agent_row(db):
    row = models.Agent(name="test_agent", type="test", status="idle", config={})
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
