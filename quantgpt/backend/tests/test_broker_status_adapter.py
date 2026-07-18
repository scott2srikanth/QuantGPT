"""Tests for OpenAlgoBrokerStatusAdapter."""

from __future__ import annotations

from app.integration.adapters.broker_status import OpenAlgoBrokerStatusAdapter
from tests.conftest import make_adapter


def test_ping_success(fake_http, cache):
    fake_http.set_response("POST", "/api/v1/ping", {"status": "success", "data": "success"})
    a = make_adapter(OpenAlgoBrokerStatusAdapter, fake_http, cache, ttl=0)
    assert a.ping() is True


def test_ping_failure(fake_http, cache):
    # no route registered -> AssertionError inside fake_http, caught by adapter
    a = make_adapter(OpenAlgoBrokerStatusAdapter, fake_http, cache, ttl=0)
    assert a.ping() is False


def test_get_status(fake_http, cache):
    fake_http.set_response("POST", "/api/v1/ping", {"status": "success", "data": "success"})
    a = make_adapter(OpenAlgoBrokerStatusAdapter, fake_http, cache, ttl=0)
    s = a.get_status()
    assert s.reachable is True
    assert s.api_key_configured is True
    assert s.base_url == "http://openalgo.test"
