"""Tests for OpenAlgoTradesAdapter."""

from __future__ import annotations

from decimal import Decimal

from app.integration.adapters.trades import OpenAlgoTradesAdapter
from app.integration.models import Side
from tests.conftest import make_adapter


def test_get_tradebook(fake_http, cache):
    fake_http.set_response(
        "POST",
        "/api/v1/tradebook",
        {"status": "success", "data": [{"tradeid": "T1", "orderid": "O1", "symbol": "X", "exchange": "NSE", "action": "BUY", "quantity": 10, "price": "100.5", "product": "MIS"}]},
    )
    a = make_adapter(OpenAlgoTradesAdapter, fake_http, cache, ttl=0)
    tb = a.get_tradebook()
    assert len(tb) == 1
    assert tb[0].trade_id == "T1"
    assert tb[0].price == Decimal("100.5")
    assert tb[0].side is Side.BUY


def test_get_trades_for_order(fake_http, cache):
    fake_http.set_response(
        "POST",
        "/api/v1/tradebook",
        {"status": "success", "data": [
            {"tradeid": "T1", "orderid": "O1", "symbol": "X", "exchange": "NSE", "action": "BUY", "quantity": 10, "price": "100", "product": "MIS"},
            {"tradeid": "T2", "orderid": "O2", "symbol": "Y", "exchange": "NSE", "action": "SELL", "quantity": 5, "price": "200", "product": "MIS"},
        ]},
    )
    a = make_adapter(OpenAlgoTradesAdapter, fake_http, cache, ttl=0)
    out = a.get_trades_for_order("O2")
    assert len(out) == 1
    assert out[0].trade_id == "T2"
