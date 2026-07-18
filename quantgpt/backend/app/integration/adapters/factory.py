"""Adapter factory.

Builds the concrete OpenAlgo adapter set from settings. This is the only
place that knows which backend is active — swapping to a different backend
means adding a new factory branch here, not editing callers.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config.settings import Settings
from app.integration.adapters.broker_status import OpenAlgoBrokerStatusAdapter
from app.integration.adapters.configuration import OpenAlgoConfigurationAdapter
from app.integration.adapters.market_data import OpenAlgoMarketDataAdapter
from app.integration.adapters.orders import OpenAlgoOrdersAdapter
from app.integration.adapters.paper_trading import OpenAlgoPaperTradingAdapter
from app.integration.adapters.positions import OpenAlgoPositionsAdapter
from app.integration.adapters.portfolio import OpenAlgoPortfolioAdapter
from app.integration.adapters.trades import OpenAlgoTradesAdapter
from app.integration.adapters.websocket import OpenAlgoWebSocketAdapter
from app.integration.cache import TTLCache
from app.integration.http_transport import HttpTransport


@dataclass
class OpenAlgoAdapterSet:
    transport: HttpTransport
    cache: TTLCache
    market_data: OpenAlgoMarketDataAdapter
    orders: OpenAlgoOrdersAdapter
    trades: OpenAlgoTradesAdapter
    positions: OpenAlgoPositionsAdapter
    portfolio: OpenAlgoPortfolioAdapter
    paper_trading: OpenAlgoPaperTradingAdapter
    broker_status: OpenAlgoBrokerStatusAdapter
    websocket: OpenAlgoWebSocketAdapter
    configuration: OpenAlgoConfigurationAdapter


def build_openalgo_adapters(settings: Settings) -> OpenAlgoAdapterSet:
    transport = HttpTransport(
        base_url=settings.openalgo_base_url,
        timeout=settings.openalgo_request_timeout_seconds,
        max_retries=settings.openalgo_max_retries,
    )
    cache = TTLCache(default_ttl=settings.openalgo_cache_ttl_seconds)
    common = dict(transport=transport, api_key=settings.openalgo_api_key, cache=cache, cache_ttl=settings.openalgo_cache_ttl_seconds)
    return OpenAlgoAdapterSet(
        transport=transport,
        cache=cache,
        market_data=OpenAlgoMarketDataAdapter(**common),
        orders=OpenAlgoOrdersAdapter(**common),
        trades=OpenAlgoTradesAdapter(**common),
        positions=OpenAlgoPositionsAdapter(**common),
        portfolio=OpenAlgoPortfolioAdapter(**common),
        paper_trading=OpenAlgoPaperTradingAdapter(**common),
        broker_status=OpenAlgoBrokerStatusAdapter(**common),
        websocket=OpenAlgoWebSocketAdapter(
            websocket_url=settings.openalgo_websocket_url,
            api_key=settings.openalgo_api_key,
        ),
        configuration=OpenAlgoConfigurationAdapter(**common),
    )
