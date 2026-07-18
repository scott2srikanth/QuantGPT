"""Tests for OpenAlgoPositionsAdapter."""

from __future__ import annotations

from decimal import Decimal

from app.integration.adapters.positions import OpenAlgoPositionsAdapter
from app.integration.models import OrderStatus, Product
from tests.conftest import make_adapter


def test_get_positions(fake_http, cache):
    fake_http.set_response(
        "POST",
        "/api/v1/positionbook",
        {"status": "success", "data": [{"symbol": "X", "exchange": "NSE", "product": "MIS", "quantity": 10, "average_price": "100", "ltp": "105", "pnl": "50"}]},
    )
    a = make_adapter(OpenAlgoPositionsAdapter, fake_http, cache, ttl=0)
    pos = a.get_positions()
    assert len(pos) == 1
    assert pos[0].quantity == 10
    assert pos[0].average_price == Decimal("100")
    assert pos[0].pnl == Decimal("50")
    assert pos[0].product is Product.MIS


def test_close_position(fake_http, cache):
    fake_http.set_response("POST", "/api/v1/closeposition", {"status": "success", "data": {"orderid": "C1"}})
    a = make_adapter(OpenAlgoPositionsAdapter, fake_http, cache, ttl=0)
    r = a.close_position("X", "NSE", "MIS")
    assert r.order_id == "C1"
    assert r.status is OrderStatus.COMPLETE
    body = fake_http.calls[0][2]
    assert body["symbol"] == "X"
    assert body["product"] == "MIS"
