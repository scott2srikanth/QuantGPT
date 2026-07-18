"""Tests for OpenAlgoPortfolioAdapter."""

from __future__ import annotations

from decimal import Decimal

from app.integration.adapters.portfolio import OpenAlgoPortfolioAdapter
from tests.conftest import make_adapter


def test_get_holdings(fake_http, cache):
    fake_http.set_response(
        "POST",
        "/api/v1/holdings",
        {"status": "success", "data": [{"symbol": "X", "exchange": "NSE", "quantity": 100, "average_price": "1000", "ltp": "1100", "pnl": "10000"}]},
    )
    a = make_adapter(OpenAlgoPortfolioAdapter, fake_http, cache, ttl=0)
    h = a.get_holdings()
    assert len(h) == 1
    assert h[0].quantity == 100
    assert h[0].pnl == Decimal("10000")


def test_get_funds(fake_http, cache):
    fake_http.set_response(
        "POST",
        "/api/v1/funds",
        {"status": "success", "data": {"available_balance": "500000", "used_margin": "100000", "realized_pnl": "5000"}},
    )
    a = make_adapter(OpenAlgoPortfolioAdapter, fake_http, cache, ttl=0)
    f = a.get_funds()
    assert f.available_balance == Decimal("500000")
    assert f.used_margin == Decimal("100000")
    assert f.realized_pnl == Decimal("5000")
