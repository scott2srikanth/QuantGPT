"""Tests for OpenAlgoPaperTradingAdapter."""

from __future__ import annotations

from app.integration.adapters.paper_trading import OpenAlgoPaperTradingAdapter
from app.integration.models import OrderRequest, OrderStatus, Product, Side
from tests.conftest import make_adapter


def test_place_paper_order_sets_analyze_flag(fake_http, cache):
    fake_http.set_response("POST", "/api/v1/placeorder", {"status": "success", "data": {"orderid": "P1"}})
    a = make_adapter(OpenAlgoPaperTradingAdapter, fake_http, cache, ttl=0)
    r = a.place_paper_order(OrderRequest(symbol="X", exchange="NSE", side=Side.BUY, quantity=10, product=Product.MIS))
    assert r.order_id == "P1"
    assert r.status is OrderStatus.COMPLETE
    body = fake_http.calls[0][2]
    assert body.get("analyze") is True


def test_get_paper_positions(fake_http, cache):
    fake_http.set_response(
        "POST",
        "/api/v1/positionbook",
        {"status": "success", "data": [{"symbol": "X", "exchange": "NSE", "product": "MIS", "quantity": 5, "average_price": "100"}]},
    )
    a = make_adapter(OpenAlgoPaperTradingAdapter, fake_http, cache, ttl=0)
    pos = a.get_paper_positions()
    assert len(pos) == 1
    assert pos[0].quantity == 5


def test_get_paper_funds(fake_http, cache):
    fake_http.set_response("POST", "/api/v1/funds", {"status": "success", "data": {"available_balance": "1000000"}})
    a = make_adapter(OpenAlgoPaperTradingAdapter, fake_http, cache, ttl=0)
    f = a.get_paper_funds()
    assert f.available_balance == __import__("decimal").Decimal("1000000")
