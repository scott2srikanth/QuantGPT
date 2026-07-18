"""Tests for OpenAlgoOrdersAdapter."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.integration.adapters.orders import OpenAlgoOrdersAdapter
from app.integration.models import OrderRequest, OrderStatus, OrderType, Product, Side
from tests.conftest import make_adapter


def test_place_order(fake_http, cache):
    fake_http.set_response("POST", "/api/v1/placeorder", {"status": "success", "data": {"orderid": "ORD123"}})
    a = make_adapter(OpenAlgoOrdersAdapter, fake_http, cache, ttl=0)
    r = a.place_order(OrderRequest(symbol="RELIANCE", exchange="NSE", side=Side.BUY, quantity=10, product=Product.MIS))
    assert r.order_id == "ORD123"
    assert r.status is OrderStatus.COMPLETE
    body = fake_http.calls[0][2]
    assert body["action"] == "BUY"
    assert body["pricetype"] == "MARKET"


def test_place_limit_order_sends_price(fake_http, cache):
    fake_http.set_response("POST", "/api/v1/placeorder", {"status": "success", "data": {"orderid": "X"}})
    a = make_adapter(OpenAlgoOrdersAdapter, fake_http, cache, ttl=0)
    a.place_order(OrderRequest(symbol="X", exchange="NSE", side=Side.BUY, quantity=1, product=Product.MIS, order_type=OrderType.LIMIT, price=Decimal("100.5")))
    body = fake_http.calls[0][2]
    assert body["pricetype"] == "LIMIT"
    assert body["price"] == "100.5"


def test_modify_order(fake_http, cache):
    fake_http.set_response("POST", "/api/v1/modifyorder", {"status": "success", "data": {"orderid": "ORD123"}})
    a = make_adapter(OpenAlgoOrdersAdapter, fake_http, cache, ttl=0)
    r = a.modify_order("ORD123", quantity=20, price=Decimal("200"))
    assert r.order_id == "ORD123"
    body = fake_http.calls[0][2]
    assert body["orderid"] == "ORD123"
    assert body["quantity"] == 20
    assert body["price"] == "200"


def test_cancel_order(fake_http, cache):
    fake_http.set_response("POST", "/api/v1/cancelorder", {"status": "success", "data": {"orderid": "ORD123"}})
    a = make_adapter(OpenAlgoOrdersAdapter, fake_http, cache, ttl=0)
    r = a.cancel_order("ORD123")
    assert r.status is OrderStatus.CANCELLED


def test_get_orderbook(fake_http, cache):
    fake_http.set_response(
        "POST",
        "/api/v1/orderbook",
        {"status": "success", "data": [{"orderid": "1", "symbol": "X", "exchange": "NSE", "action": "BUY", "quantity": 10, "product": "MIS", "pricetype": "MARKET", "order_status": "complete"}]},
    )
    a = make_adapter(OpenAlgoOrdersAdapter, fake_http, cache, ttl=0)
    ob = a.get_orderbook()
    assert len(ob) == 1
    assert ob[0].order_id == "1"
    assert ob[0].side is Side.BUY
    assert ob[0].status is OrderStatus.COMPLETE


def test_get_order(fake_http, cache):
    fake_http.set_response("POST", "/api/v1/orderstatus", {"status": "success", "data": {"orderid": "1", "symbol": "X", "exchange": "NSE", "action": "BUY", "quantity": 10, "product": "MIS", "pricetype": "MARKET", "order_status": "open"}})
    a = make_adapter(OpenAlgoOrdersAdapter, fake_http, cache, ttl=0)
    o = a.get_order("1")
    assert o.status is OrderStatus.OPEN
