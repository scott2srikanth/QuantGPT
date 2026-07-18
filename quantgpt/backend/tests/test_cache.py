"""Tests for TTLCache."""

from __future__ import annotations

import time

from app.integration.cache import TTLCache


def test_set_get():
    c = TTLCache(default_ttl=10)
    c.set("k", "v")
    assert c.get("k") == "v"


def test_miss():
    c = TTLCache()
    assert c.get("missing") is None


def test_get_or_set():
    c = TTLCache(default_ttl=10)
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        return "computed"

    assert c.get_or_set("k", factory) == "computed"
    assert c.get_or_set("k", factory) == "computed"
    assert calls["n"] == 1


def test_invalidate():
    c = TTLCache(default_ttl=10)
    c.set("k", "v")
    c.invalidate("k")
    assert c.get("k") is None


def test_expiry():
    c = TTLCache(default_ttl=1)
    c.set("k", "v", ttl=0)  # immediate expiry
    time.sleep(0.01)
    assert c.get("k") is None


def test_clear():
    c = TTLCache()
    c.set("a", 1)
    c.set("b", 2)
    c.clear()
    assert c.size() == 0
