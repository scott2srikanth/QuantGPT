"""Tests for OpenAlgoConfigurationAdapter."""

from __future__ import annotations

from app.integration.adapters.configuration import OpenAlgoConfigurationAdapter
from tests.conftest import make_adapter


def test_get_config(fake_http, cache):
    fake_http.set_response("POST", "/api/v1/settings", {"status": "success", "data": {"value": "true"}})
    a = make_adapter(OpenAlgoConfigurationAdapter, fake_http, cache, ttl=0)
    assert a.get_config("analyze_mode") == "true"
    body = fake_http.calls[0][2]
    assert body["action"] == "get"
    assert body["key"] == "analyze_mode"


def test_set_config(fake_http, cache):
    fake_http.set_response("POST", "/api/v1/settings", {"status": "success", "data": {}})
    a = make_adapter(OpenAlgoConfigurationAdapter, fake_http, cache, ttl=0)
    a.set_config("analyze_mode", "false")
    body = fake_http.calls[0][2]
    assert body["action"] == "set"
    assert body["value"] == "false"


def test_list_config(fake_http, cache):
    fake_http.set_response("POST", "/api/v1/settings", {"status": "success", "data": {"analyze_mode": "true", "log_level": "INFO"}})
    a = make_adapter(OpenAlgoConfigurationAdapter, fake_http, cache, ttl=0)
    cfg = a.list_config()
    assert cfg["analyze_mode"] == "true"
    assert cfg["log_level"] == "INFO"


def test_get_config_returns_none_on_error(fake_http, cache):
    # no route -> exception -> caught -> None
    a = make_adapter(OpenAlgoConfigurationAdapter, fake_http, cache, ttl=0)
    assert a.get_config("missing") is None
