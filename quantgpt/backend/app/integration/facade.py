"""IntegrationFacade — the single surface QuantGPT uses to reach its trading backend.

This facade delegates to the active adapter set (OpenAlgo today, swappable
later). All of QuantGPT depends on this facade, never on a concrete adapter
or on OpenAlgo directly. This is the seam that lets OpenAlgo be replaced by
another backend without touching calling code.

The facade exposes typed, backend-neutral methods grouped by capability:
  - market_data
  - orders
  - trades
  - positions
  - portfolio
  - paper_trading
  - broker_status
  - websocket
  - configuration
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.config.settings import Settings
from app.integration.adapters.factory import OpenAlgoAdapterSet, build_openalgo_adapters
from app.integration.models import (
    BrokerStatus,
    Candle,
    Funds,
    Holding,
    Instrument,
    MarketDepth,
    OptionChain,
    OrderRecord,
    OrderRequest,
    OrderResponse,
    Position,
    Quote,
    SubscriptionMode,
    Tick,
    TradeRecord,
)


class IntegrationFacade:
    """Single entrypoint to the trading backend.

    Today this wraps an OpenAlgo adapter set. To swap backends, build a
    different adapter set implementing the same neutral interfaces and
    pass it to the constructor — no other code changes required.
    """

    def __init__(self, adapters: OpenAlgoAdapterSet, *, websocket_url: str) -> None:
        self._a = adapters
        self._websocket_url = websocket_url

    @classmethod
    def from_settings(cls, settings: Settings) -> "IntegrationFacade":
        adapters = build_openalgo_adapters(settings)
        return cls(adapters, websocket_url=settings.openalgo_websocket_url)

    # ── lifecycle ──
    def close(self) -> None:
        self._a.transport.close()

    # ── Market Data ──
    def quote(self, symbol: str, exchange: str) -> Quote:
        return self._a.market_data.get_quote(symbol, exchange)

    def quotes(self, symbols: list[tuple[str, str]]) -> list[Quote]:
        return self._a.market_data.get_quotes(symbols)

    def depth(self, symbol: str, exchange: str) -> MarketDepth:
        return self._a.market_data.get_depth(symbol, exchange)

    def history(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        *,
        start: str | None = None,
        end: str | None = None,
        limit: int = 100,
    ) -> list[Candle]:
        return self._a.market_data.get_history(symbol, exchange, interval, start=start, end=end, limit=limit)

    def search(self, query: str) -> list[Instrument]:
        return self._a.market_data.search_instruments(query)

    def option_chain(self, symbol: str, exchange: str) -> OptionChain:
        return self._a.market_data.get_option_chain(symbol, exchange)

    # ── Orders ──
    def place_order(self, request: OrderRequest) -> OrderResponse:
        return self._a.orders.place_order(request)

    def modify_order(self, order_id: str, **kwargs: Any) -> OrderResponse:
        return self._a.orders.modify_order(order_id, **kwargs)

    def cancel_order(self, order_id: str) -> OrderResponse:
        return self._a.orders.cancel_order(order_id)

    def orderbook(self) -> list[OrderRecord]:
        return self._a.orders.get_orderbook()

    def order(self, order_id: str) -> OrderRecord:
        return self._a.orders.get_order(order_id)

    # ── Trades ──
    def tradebook(self) -> list[TradeRecord]:
        return self._a.trades.get_tradebook()

    def trades_for_order(self, order_id: str) -> list[TradeRecord]:
        return self._a.trades.get_trades_for_order(order_id)

    # ── Positions ──
    def positions(self) -> list[Position]:
        return self._a.positions.get_positions()

    def close_position(self, symbol: str, exchange: str, product: str) -> OrderResponse:
        return self._a.positions.close_position(symbol, exchange, product)

    # ── Portfolio ──
    def holdings(self) -> list[Holding]:
        return self._a.portfolio.get_holdings()

    def funds(self) -> Funds:
        return self._a.portfolio.get_funds()

    # ── Paper Trading ──
    def place_paper_order(self, request: OrderRequest) -> OrderResponse:
        return self._a.paper_trading.place_paper_order(request)

    def paper_orderbook(self) -> list[OrderRecord]:
        return self._a.paper_trading.get_paper_orderbook()

    def paper_positions(self) -> list[Position]:
        return self._a.paper_trading.get_paper_positions()

    def paper_funds(self) -> Funds:
        return self._a.paper_trading.get_paper_funds()

    # ── Broker Status ──
    def broker_status(self) -> BrokerStatus:
        s = self._a.broker_status.get_status()
        # fill websocket url (the broker_status adapter doesn't know it)
        return BrokerStatus(
            base_url=s.base_url,
            reachable=s.reachable,
            api_key_configured=s.api_key_configured,
            websocket_url=self._websocket_url,
            detail=s.detail,
        )

    def ping(self) -> bool:
        return self._a.broker_status.ping()

    # ── WebSocket ──
    async def ws_connect(self) -> None:
        await self._a.websocket.connect()

    async def ws_disconnect(self) -> None:
        await self._a.websocket.disconnect()

    async def ws_subscribe(
        self, symbols: list[tuple[str, str]], mode: SubscriptionMode = SubscriptionMode.LTP
    ) -> None:
        await self._a.websocket.subscribe(symbols, mode)

    async def ws_unsubscribe(self, symbols: list[tuple[str, str]]) -> None:
        await self._a.websocket.unsubscribe(symbols)

    def ws_stream(self) -> AsyncIterator[Tick]:
        return self._a.websocket.stream()

    # ── Configuration ──
    def get_config(self, key: str) -> str | None:
        return self._a.configuration.get_config(key)

    def set_config(self, key: str, value: str) -> None:
        self._a.configuration.set_config(key, value)

    def list_config(self) -> dict[str, str]:
        return self._a.configuration.list_config()

    # ── introspection ──
    @property
    def cache_size(self) -> int:
        return self._a.cache.size()

    def clear_cache(self) -> None:
        self._a.cache.clear()
