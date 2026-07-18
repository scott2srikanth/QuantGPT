"""Backend-neutral interfaces (abstract base classes).

Every adapter implements these ABCs. The rest of QuantGPT depends only on
these interfaces, never on a concrete adapter — so OpenAlgo can later be
replaced by another backend (Zerodha Kite directly, a custom exchange,
a backtest engine, etc.) without touching calling code.

The IntegrationFacade (facade.py) exposes a single surface that delegates
to the active adapter for each capability.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Protocol

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


# ── Market Data ──
class MarketDataAdapter(Protocol):
    def get_quote(self, symbol: str, exchange: str) -> Quote: ...
    def get_quotes(self, symbols: list[tuple[str, str]]) -> list[Quote]: ...
    def get_depth(self, symbol: str, exchange: str) -> MarketDepth: ...
    def get_history(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        *,
        start: str | None = None,
        end: str | None = None,
        limit: int = 100,
    ) -> list[Candle]: ...
    def search_instruments(self, query: str) -> list[Instrument]: ...
    def get_option_chain(self, symbol: str, exchange: str) -> OptionChain: ...


# ── Orders ──
class OrdersAdapter(Protocol):
    def place_order(self, request: OrderRequest) -> OrderResponse: ...
    def modify_order(
        self,
        order_id: str,
        *,
        quantity: int | None = None,
        price: Decimal | None = None,
        order_type: str | None = None,
        trigger_price: Decimal | None = None,
    ) -> OrderResponse: ...
    def cancel_order(self, order_id: str) -> OrderResponse: ...
    def get_orderbook(self) -> list[OrderRecord]: ...
    def get_order(self, order_id: str) -> OrderRecord: ...


# ── Trades ──
class TradesAdapter(Protocol):
    def get_tradebook(self) -> list[TradeRecord]: ...
    def get_trades_for_order(self, order_id: str) -> list[TradeRecord]: ...


# ── Positions ──
class PositionsAdapter(Protocol):
    def get_positions(self) -> list[Position]: ...
    def close_position(self, symbol: str, exchange: str, product: str) -> OrderResponse: ...


# ── Portfolio ──
class PortfolioAdapter(Protocol):
    def get_holdings(self) -> list[Holding]: ...
    def get_funds(self) -> Funds: ...


# ── Paper Trading ──
class PaperTradingAdapter(Protocol):
    def place_paper_order(self, request: OrderRequest) -> OrderResponse: ...
    def get_paper_orderbook(self) -> list[OrderRecord]: ...
    def get_paper_positions(self) -> list[Position]: ...
    def get_paper_funds(self) -> Funds: ...


# ── Broker Status ──
class BrokerStatusAdapter(Protocol):
    def get_status(self) -> BrokerStatus: ...
    def ping(self) -> bool: ...


# ── WebSocket Streams ──
class WebSocketAdapter(Protocol):
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def subscribe(
        self, symbols: list[tuple[str, str]], mode: SubscriptionMode = SubscriptionMode.LTP
    ) -> None: ...
    async def unsubscribe(self, symbols: list[tuple[str, str]]) -> None: ...
    def stream(self) -> AsyncIterator[Tick]: ...


# ── Configuration ──
class ConfigurationAdapter(Protocol):
    def get_config(self, key: str) -> str | None: ...
    def set_config(self, key: str, value: str) -> None: ...
    def list_config(self) -> dict[str, str]: ...
