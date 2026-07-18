"""Tests for OpenAlgoMarketDataAdapter."""

from __future__ import annotations

from decimal import Decimal

from app.integration.adapters.market_data import OpenAlgoMarketDataAdapter
from tests.conftest import make_adapter


def test_get_quote(fake_http, cache):
    fake_http.set_response(
        "POST",
        "/api/v1/quotes",
        {"status": "success", "data": {"RELIANCE": {"ltp": "2450.50", "open": "2400.00", "volume": 1000}}},
    )
    a = make_adapter(OpenAlgoMarketDataAdapter, fake_http, cache)
    q = a.get_quote("RELIANCE", "NSE")
    assert q.symbol == "RELIANCE"
    assert q.exchange == "NSE"
    assert q.ltp == Decimal("2450.50")
    assert q.open == Decimal("2400.00")
    assert q.volume == 1000
    # apikey was sent
    assert fake_http.calls[0][2]["apikey"] == "test-key"


def test_get_quote_cached(fake_http, cache):
    fake_http.set_response(
        "POST",
        "/api/v1/quotes",
        {"status": "success", "data": {"RELIANCE": {"ltp": "100"}}},
    )
    a = make_adapter(OpenAlgoMarketDataAdapter, fake_http, cache, ttl=60)
    a.get_quote("RELIANCE", "NSE")
    a.get_quote("RELIANCE", "NSE")
    # only one HTTP call due to cache
    assert len(fake_http.calls) == 1


def test_get_quotes_groups_by_exchange(fake_http, cache):
    fake_http.set_response(
        "POST",
        "/api/v1/multiquotes",
        {"status": "success", "data": {"RELIANCE": {"ltp": "100"}, "INFY": {"ltp": "200"}}},
    )
    a = make_adapter(OpenAlgoMarketDataAdapter, fake_http, cache, ttl=0)
    out = a.get_quotes([("RELIANCE", "NSE"), ("INFY", "NSE")])
    assert len(out) == 2
    assert out[0].ltp == Decimal("100")
    assert out[1].ltp == Decimal("200")


def test_get_depth(fake_http, cache):
    fake_http.set_response(
        "POST",
        "/api/v1/depth",
        {"status": "success", "data": {"RELIANCE": {"bids": [{"price": "100", "quantity": 5, "orders": 2}], "asks": [{"price": "101", "quantity": 3}]}}},
    )
    a = make_adapter(OpenAlgoMarketDataAdapter, fake_http, cache, ttl=0)
    d = a.get_depth("RELIANCE", "NSE")
    assert d.bids[0].price == Decimal("100")
    assert d.bids[0].quantity == 5
    assert d.asks[0].price == Decimal("101")


def test_get_history(fake_http, cache):
    fake_http.set_response(
        "POST",
        "/api/v1/history",
        {"status": "success", "data": [{"timestamp": "2026-07-18T09:15:00", "open": "100", "high": "101", "low": "99", "close": "100.5", "volume": 500}]},
    )
    a = make_adapter(OpenAlgoMarketDataAdapter, fake_http, cache, ttl=0)
    candles = a.get_history("RELIANCE", "NSE", "1m")
    assert len(candles) == 1
    assert candles[0].close == Decimal("100.5")
    assert candles[0].volume == 500


def test_search_instruments(fake_http, cache):
    fake_http.set_response(
        "GET",
        "/api/v1/search",
        {"status": "success", "data": [{"symbol": "RELIANCE", "exchange": "NSE", "token": "1234"}]},
    )
    a = make_adapter(OpenAlgoMarketDataAdapter, fake_http, cache, ttl=0)
    out = a.search_instruments("RELIANCE")
    assert out[0].symbol == "RELIANCE"
    assert out[0].token == "1234"


def test_get_option_chain(fake_http, cache):
    fake_http.set_response(
        "POST",
        "/api/v1/optionchain",
        {"status": "success", "data": {"underlying_ltp": "100", "strikes": [{"strike": "100", "ce": {"ltp": "5"}, "pe": {"ltp": "4"}}]}},
    )
    a = make_adapter(OpenAlgoMarketDataAdapter, fake_http, cache, ttl=0)
    oc = a.get_option_chain("NIFTY", "NFO")
    assert oc.underlying_ltp == Decimal("100")
    assert oc.strikes[0].strike == Decimal("100")
    assert oc.strikes[0].ce.ltp == Decimal("5")
    assert oc.strikes[0].pe.ltp == Decimal("4")


def test_error_envelope_raises(fake_http, cache):
    fake_http.set_response("POST", "/api/v1/quotes", {"status": "error", "message": "bad symbol"})
    a = make_adapter(OpenAlgoMarketDataAdapter, fake_http, cache, ttl=0)
    import pytest
    from app.integration.exceptions import BackendValidationError
    with pytest.raises(BackendValidationError):
        a.get_quote("BAD", "NSE")
