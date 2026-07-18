"""API tests for the Strategy Research Engine endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.integration.models import Candle
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def make_candles(n: int = 200) -> list[Candle]:
    import random
    random.seed(42)
    candles = []
    price = 100.0
    for i in range(n):
        o = price
        c = price + 0.5 + random.uniform(-1, 1)
        h = max(o, c) + 0.5
        lo = min(o, c) - 0.5
        candles.append(Candle(
            timestamp=datetime(2024, 1, 1) + timedelta(days=i),
            open=Decimal(str(round(o, 2))),
            high=Decimal(str(round(h, 2))),
            low=Decimal(str(round(lo, 2))),
            close=Decimal(str(round(c, 2))),
            volume=1000,
        ))
        price = c
    return candles


class TestStrategyEndpoints:
    def test_list_strategies(self, client):
        r = client.get("/api/v1/strategies")
        assert r.status_code == 200
        body = r.json()
        assert "strategies" in body
        assert body["count"] >= 7
        names = [s["name"] for s in body["strategies"]]
        assert "momentum" in names
        assert "breakout" in names

    def test_get_strategy(self, client):
        r = client.get("/api/v1/strategies/momentum")
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "momentum"
        assert body["display_name"] == "Momentum"

    def test_get_strategy_not_found(self, client):
        r = client.get("/api/v1/strategies/nonexistent")
        assert r.status_code == 404

    def test_get_strategy_config(self, client):
        r = client.get("/api/v1/strategies/momentum/config")
        assert r.status_code == 200
        body = r.json()
        assert "schema" in body
        assert "defaults" in body
        assert "fast_ema" in body["defaults"]


class TestMarketplaceEndpoints:
    def test_list_marketplace(self, client):
        r = client.get("/api/v1/marketplace")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        assert len(body) >= 7

    def test_get_marketplace_listing(self, client):
        r = client.get("/api/v1/marketplace/momentum")
        assert r.status_code == 200
        body = r.json()
        assert body["strategy_name"] == "momentum"

    def test_get_marketplace_listing_not_found(self, client):
        r = client.get("/api/v1/marketplace/nonexistent")
        assert r.status_code == 404

    def test_publish_strategy(self, client):
        r = client.post("/api/v1/marketplace/momentum/publish", json={
            "title": "Test Publish",
            "description": "Test",
            "author": "tester",
            "tags": ["momentum", "test"],
        })
        assert r.status_code == 200
        body = r.json()
        assert body["title"] == "Test Publish"
        assert body["author"] == "tester"

    def test_rate_strategy(self, client):
        r = client.post("/api/v1/marketplace/momentum/rate", json={"rating": 4.5})
        assert r.status_code == 200
        body = r.json()
        assert body["rating"] == 4.5

    def test_rate_strategy_invalid(self, client):
        r = client.post("/api/v1/marketplace/momentum/rate", json={"rating": 6.0})
        assert r.status_code == 422  # Pydantic validation (ge=0, le=5)

    def test_rate_strategy_not_found(self, client):
        r = client.post("/api/v1/marketplace/nonexistent/rate", json={"rating": 3.0})
        assert r.status_code == 404

    def test_download_strategy(self, client):
        r = client.post("/api/v1/marketplace/momentum/download")
        assert r.status_code == 200
        body = r.json()
        assert "strategy" in body
        assert "config_schema" in body

    def test_download_strategy_not_found(self, client):
        r = client.post("/api/v1/marketplace/nonexistent/download")
        assert r.status_code == 404

    def test_feature_strategy(self, client):
        r = client.post("/api/v1/marketplace/momentum/feature")
        assert r.status_code == 200
        body = r.json()
        assert body["is_featured"] is True


class TestPluginEndpoints:
    def test_load_plugin_no_paths(self, client):
        r = client.post("/api/v1/plugins/load", json={})
        assert r.status_code == 200
        body = r.json()
        assert body["loaded"] is False
        assert "error" in body
