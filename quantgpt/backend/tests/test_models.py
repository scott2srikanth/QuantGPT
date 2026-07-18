"""Tests for the neutral models + exceptions."""

from __future__ import annotations

from decimal import Decimal

from app.integration.exceptions import (
    BackendAuthError,
    BackendRateLimitError,
    BackendServerError,
    BackendValidationError,
    IntegrationError,
)
from app.integration.models import (
    OrderRequest,
    OrderType,
    Product,
    Quote,
    Side,
    Tick,
)


def test_quote_is_frozen():
    q = Quote(symbol="RELIANCE", exchange="NSE", ltp=Decimal("2450.50"))
    try:
        q.ltp = Decimal("1")  # type: ignore[misc]
        assert False, "should be frozen"
    except Exception:
        pass


def test_order_request_defaults():
    r = OrderRequest(symbol="RELIANCE", exchange="NSE", side=Side.BUY, quantity=10, product=Product.MIS)
    assert r.order_type is OrderType.MARKET
    assert r.price is None


def test_tick_decimal():
    t = Tick(symbol="X", exchange="NSE", ltp=Decimal("100.5"))
    assert t.ltp == Decimal("100.5")


def test_exceptions_hierarchy():
    for exc in (BackendAuthError, BackendRateLimitError, BackendServerError, BackendValidationError):
        assert issubclass(exc, IntegrationError)
