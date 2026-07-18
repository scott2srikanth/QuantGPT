"""Backend-neutral domain models.

These are the canonical QuantGPT types for market data, orders, trades,
positions, portfolio, and broker status. Every adapter maps its
backend-specific responses into these so the rest of QuantGPT never
depends on a particular broker's schema.

OpenAlgo field names are intentionally NOT reused here — these are
QuantGPT's own contracts. The OpenAlgo adapter is responsible for
translating between the two.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


class Product(str, Enum):
    CNC = "CNC"
    NRML = "NRML"
    MIS = "MIS"


class OrderStatus(str, Enum):
    OPEN = "open"
    COMPLETE = "complete"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class Validity(str, Enum):
    DAY = "DAY"
    IOC = "IOC"


# ── Market Data ──
class Quote(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: str
    exchange: str
    ltp: Decimal
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal | None = None
    volume: int | None = None
    timestamp: datetime | None = None


class DepthLevel(BaseModel):
    model_config = ConfigDict(frozen=True)
    price: Decimal
    quantity: int
    orders: int | None = None


class MarketDepth(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: str
    exchange: str
    bids: list[DepthLevel] = Field(default_factory=list)
    asks: list[DepthLevel] = Field(default_factory=list)
    timestamp: datetime | None = None


class Candle(BaseModel):
    model_config = ConfigDict(frozen=True)
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int | None = None


class Instrument(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: str
    exchange: str
    token: str | None = None
    name: str | None = None
    instrument_type: str | None = None
    expiry: datetime | None = None
    strike: Decimal | None = None
    lot_size: int | None = None


class OptionChainEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    strike: Decimal
    ce: Quote | None = None
    pe: Quote | None = None


class OptionChain(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: str
    exchange: str
    underlying_ltp: Decimal | None = None
    strikes: list[OptionChainEntry] = Field(default_factory=list)


# ── Orders ──
class OrderRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: str
    exchange: str
    side: Side
    quantity: int
    product: Product
    order_type: OrderType = OrderType.MARKET
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    validity: Validity = Validity.DAY
    disclosed_quantity: int | None = None
    strategy: str | None = None
    metadata: dict[str, Any] | None = None


class OrderResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    order_id: str
    status: OrderStatus
    rejected_reason: str | None = None
    average_price: Decimal | None = None
    filled_quantity: int | None = None
    timestamp: datetime | None = None


class OrderRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    order_id: str
    symbol: str
    exchange: str
    side: Side
    quantity: int
    product: Product
    order_type: OrderType
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    status: OrderStatus
    average_price: Decimal | None = None
    filled_quantity: int | None = None
    rejected_reason: str | None = None
    strategy: str | None = None
    timestamp: datetime | None = None


# ── Trades ──
class TradeRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    trade_id: str
    order_id: str
    symbol: str
    exchange: str
    side: Side
    quantity: int
    price: Decimal
    product: Product
    strategy: str | None = None
    timestamp: datetime | None = None


# ── Positions ──
class Position(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: str
    exchange: str
    product: Product
    quantity: int
    average_price: Decimal
    ltp: Decimal | None = None
    pnl: Decimal | None = None
    pnl_percent: Decimal | None = None


# ── Portfolio ──
class Holding(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: str
    exchange: str
    quantity: int
    average_price: Decimal
    ltp: Decimal | None = None
    pnl: Decimal | None = None


class Funds(BaseModel):
    model_config = ConfigDict(frozen=True)
    total_capital: Decimal | None = None
    available_balance: Decimal
    used_margin: Decimal | None = None
    realized_pnl: Decimal | None = None
    unrealized_pnl: Decimal | None = None


# ── Broker status ──
class BrokerStatus(BaseModel):
    model_config = ConfigDict(frozen=True)
    base_url: str
    reachable: bool
    api_key_configured: bool
    websocket_url: str
    detail: str | None = None


# ── WebSocket stream ──
class Tick(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: str
    exchange: str
    ltp: Decimal
    timestamp: datetime | None = None
    volume: int | None = None


class SubscriptionMode(str, Enum):
    LTP = "ltp"
    QUOTE = "quote"
    DEPTH = "depth"
