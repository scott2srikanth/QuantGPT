"""Smoke tests for the FastAPI app."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_root():
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["name"] == "QuantGPT"


def test_health():
    client = TestClient(app)
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
