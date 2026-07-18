"""Tests for the IntegrationFacade."""

from __future__ import annotations

from decimal import Decimal

from app.integration.adapters.factory import OpenAlgoAdapterSet
from app.integration.adapters.broker_status import OpenAlgoBrokerStatusAdapter
from app.integration.adapters.market_data import OpenAlgoMarketDataAdapter
from app.integration.adapters.orders import OpenAlgoOrdersAdapter
from app.integration.adapters.trades import OpenAlgoTradesAdapter
from app.integration.adapters.positions import OpenAlgoPositionsAdapter
from app.integration.adapters.portfolio import OpenAlgoPortfolioAdapter
from app.integration.adapters.paper_trading import OpenAlgoPaperTradingAdapter
from app.integration.adapters.configuration import OpenAlgoConfigurationAdapter
from app.integration.adapters.websocket import OpenAlgoWebSocketAdapter
from app.integration.cache import TTLCache
from app.integration.facade import IntegrationFacade
from app.integration.models import OrderRequest, OrderStatus, Product, Side
from tests.conftest import FakeHttp


def _build_facade(fake_http: FakeHttp) -> IntegrationFacade:
    cache = TTLCache(default_ttl=0)
    common = dict(transport=fake_http, api_key="test-key", cache=cache, cache_ttl=0)
    adapters = OpenAlgoAdapterSet(
        transport=fake_http,
        cache=cache,
        market_data=OpenAlgoMarketDataAdapter(**common),
        orders=OpenAlgoOrdersAdapter(**common),
        trades=OpenAlgoTradesAdapter(**common),
        positions=OpenAlgoPositionsAdapter(**common),
        portfolio=OpenAlgoPortfolioAdapter(**common),
        paper_trading=OpenAlgoPaperTradingAdapter(**common),
        broker_status=OpenAlgoBrokerStatusAdapter(**common),
        websocket=OpenAlgoWebSocketAdapter(websocket_url="ws://test", api_key="test-key"),
        configuration=OpenAlgoConfigurationAdapter(**common),
    )
    return IntegrationFacade(adapters, websocket_url="ws://openalgo:8765")


def test_facade_quote(fake_http):
    fake_http.set_response("POST", "/api/v1/quotes", {"status": "success", "data": {"X": {"ltp": "100"}}})
    f = _build_facade(fake_http)
    q = f.quote("X", "NSE")
    assert q.ltp == Decimal("100")


def test_facade_place_order(fake_http):
    fake_http.set_response("POST", "/api/v1/placeorder", {"status": "success", "data": {"orderid": "O1"}})
    f = _build_facade(fake_http)
    r = f.place_order(OrderRequest(symbol="X", exchange="NSE", side=Side.BUY, quantity=10, product=Product.MIS))
    assert r.order_id == "O1"
    assert r.status is OrderStatus.COMPLETE


def test_facade_broker_status_fills_ws_url(fake_http):
    fake_http.set_response("POST", "/api/v1/ping", {"status": "success", "data": "success"})
    f = _build_facade(fake_http)
    s = f.broker_status()
    assert s.reachable is True
    assert s.websocket_url == "ws://openalgo:8765"


def test_facade_paper_order_uses_paper_adapter(fake_http):
    fake_http.set_response("POST", "/api/v1/placeorder", {"status": "success", "data": {"orderid": "P1"}})
    f = _build_facade(fake_http)
    r = f.place_paper_order(OrderRequest(symbol="X", exchange="NSE", side=Side.BUY, quantity=1, product=Product.MIS))
    assert r.order_id == "P1"
    body = fake_http.calls[0][2]
    assert body.get("analyze") is True


def test_facade_clear_cache(fake_http):
    fake_http.set_response("POST", "/api/v1/quotes", {"status": "success", "data": {"X": {"ltp": "100"}}})
    f = _build_facade(fake_http)
    f.quote("X", "NSE")
    assert f.cache_size >= 1
    f.clear_cache()
    assert f.cache_size == 0
