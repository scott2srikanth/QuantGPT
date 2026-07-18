# OpenAlgo Integration Layer

The Integration Layer is the **only** part of QuantGPT permitted to talk to OpenAlgo. Everything else in QuantGPT depends on this layer, never on OpenAlgo directly. OpenAlgo itself is never modified — QuantGPT is an external client of its REST `/api/v1` and WebSocket proxy (port 8765).

This document describes the architecture, interfaces, adapters, and how to replace OpenAlgo with another backend.

## Architecture

```
┌─────────────────────────── QuantGPT ───────────────────────────┐
│                                                                │
│   API routers  ──►  services  ──►  IntegrationFacade           │
│                                          │                     │
│                          ┌───────────────┴───────────────┐      │
│                          │                               │      │
│                  neutral interfaces               adapters       │
│                  (models.py,                       (adapters/)  │
│                   interfaces.py)                        │        │
│                                               ┌────────┴───────┐  │
│                                               │ base adapter    │  │
│                                               │ HttpTransport   │  │
│                                               │ TTLCache         │  │
│                                               └────────┬─────────┘  │
│                                                        │           │
└────────────────────────────────────────────────────────┼───────────┘
                                                         │
                                          ┌──────────────┴──────────────┐
                                          │   OpenAlgo (unmodified)      │
                                          │   REST /api/v1  +  WS :8765  │
                                          └─────────────────────────────┘
```

### Design principles

1. **Never duplicate OpenAlgo.** The layer translates OpenAlgo's responses into QuantGPT's own neutral models. It does not mirror OpenAlgo's schema or re-implement its logic.
2. **Never modify OpenAlgo.** QuantGPT is an external client. All access is via HTTP REST and WebSocket.
3. **Interfaces first.** Every capability is defined as a `Protocol` in `interfaces.py`. Adapters implement these protocols. The rest of QuantGPT depends on the protocols, not on concrete adapters.
4. **One facade.** `IntegrationFacade` is the single entrypoint. Callers use `facade.quote(...)`, `facade.place_order(...)`, etc. They never touch adapters or OpenAlgo directly.
5. **Swappable backend.** To replace OpenAlgo, build a new adapter set implementing the same protocols and pass it to the facade. No other code changes.

## Module map

```
backend/app/integration/
├── __init__.py
├── exceptions.py          # Backend-neutral exceptions
├── models.py              # Neutral domain models (Quote, Order, Position, etc.)
├── interfaces.py          # Protocol interfaces (one per capability)
├── http_transport.py      # Pooled HTTP client + retry + error translation
├── cache.py               # In-memory TTL cache
├── facade.py              # IntegrationFacade — the single entrypoint
└── adapters/
    ├── __init__.py
    ├── base.py            # BaseOpenAlgoAdapter (shared transport + helpers)
    ├── factory.py         # build_openalgo_adapters() — builds the adapter set
    ├── market_data.py     # quotes, depth, history, search, option chain
    ├── orders.py          # place, modify, cancel, orderbook, order status
    ├── trades.py          # tradebook, trades for order
    ├── positions.py       # positions, close position
    ├── portfolio.py       # holdings, funds
    ├── paper_trading.py   # paper orders, paper orderbook/positions/funds
    ├── broker_status.py   # reachability + ping
    ├── websocket.py        # WS subscribe/unsubscribe + tick stream
    └── configuration.py   # get/set/list backend settings
```

## Neutral models

Defined in `models.py`. These are QuantGPT's canonical types — frozen Pydantic models. Every adapter maps its backend-specific responses into these.

| Model | Used by |
|---|---|
| `Quote` | market data |
| `MarketDepth`, `DepthLevel` | market data |
| `Candle` | market data (history) |
| `Instrument` | market data (search) |
| `OptionChain`, `OptionChainEntry` | market data |
| `OrderRequest`, `OrderResponse`, `OrderRecord` | orders, paper trading |
| `TradeRecord` | trades |
| `Position` | positions, paper trading |
| `Holding`, `Funds` | portfolio, paper trading |
| `BrokerStatus` | broker status |
| `Tick`, `SubscriptionMode` | websocket |

Enums: `Side` (BUY/SELL), `OrderType` (MARKET/LIMIT/SL/SL-M), `Product` (CNC/NRML/MIS), `OrderStatus`, `Validity`.

## Interfaces

Defined in `interfaces.py` as `typing.Protocol`. Each capability has its own protocol so a backend can implement only the capabilities it supports:

| Protocol | Methods |
|---|---|
| `MarketDataAdapter` | `get_quote`, `get_quotes`, `get_depth`, `get_history`, `search_instruments`, `get_option_chain` |
| `OrdersAdapter` | `place_order`, `modify_order`, `cancel_order`, `get_orderbook`, `get_order` |
| `TradesAdapter` | `get_tradebook`, `get_trades_for_order` |
| `PositionsAdapter` | `get_positions`, `close_position` |
| `PortfolioAdapter` | `get_holdings`, `get_funds` |
| `PaperTradingAdapter` | `place_paper_order`, `get_paper_orderbook`, `get_paper_positions`, `get_paper_funds` |
| `BrokerStatusAdapter` | `get_status`, `ping` |
| `WebSocketAdapter` | `connect`, `disconnect`, `subscribe`, `unsubscribe`, `stream` |
| `ConfigurationAdapter` | `get_config`, `set_config`, `list_config` |

## Exceptions

All errors are translated into backend-neutral exceptions in `exceptions.py`:

| Exception | When |
|---|---|
| `IntegrationError` | base class |
| `BackendUnreachableError` | network / connection refused |
| `BackendAuthError` | 401 / 403 / WS auth rejected |
| `BackendRateLimitError` | 429 |
| `BackendValidationError` | 4xx (except 429) or OpenAlgo `{"status":"error"}` |
| `BackendNotFoundError` | 404 |
| `BackendServerError` | 5xx or invalid JSON |
| `BackendTimeoutError` | request timeout |
| `AdapterNotImplementedError` | capability not supported by active backend |

## Cross-cutting concerns

### Connection pooling

`HttpTransport` wraps a single `httpx.Client` with `Limits(max_connections=20, max_keepalive_connections=10)`. The client is reused across all requests for the lifetime of the adapter set. The facade's `close()` releases it.

### Retry logic

`HttpTransport._request` uses `tenacity` with:
- **Retry on:** `ConnectError`, `ReadTimeout`, `WriteTimeout`, `PoolTimeout`, `BackendRateLimitError`, `BackendServerError`
- **Stop after:** `max_retries` (from `OPENALGO_MAX_RETRIES`, default 3)
- **Backoff:** exponential, multiplier 0.5s, max 5s
- **No retry on:** 4xx (except 429), auth errors, validation errors — these fail fast

The WebSocket adapter has its own reconnect loop with exponential backoff (1s → 30s max). Auth failures propagate immediately (no retry).

### Caching

`TTLCache` (in-memory, per-process) caches market-data responses. Default TTL from `OPENALGO_CACHE_TTL_SECONDS` (30s). Used by:
- `get_quote` — keyed by `quote:{exchange}:{symbol}`
- `search_instruments` — keyed by `search:{query}`
- `get_option_chain` — keyed by `optionchain:{exchange}:{symbol}`

The cache is injectable and swappable. To use Redis instead, replace `TTLCache` with a Redis-backed implementation that exposes the same `get_or_set`/`invalidate`/`clear` interface.

### Logging

All adapters log via `structlog` with a logger named `app.integration.{AdapterClassName}`. The HTTP transport logs every request at debug level. The WS adapter logs connect/disconnect/subscribe/recv events. Errors are logged with full exception info.

## Usage

### From a service

```python
from app.core.container import get_container

facade = get_container().integration

# market data
quote = facade.quote("RELIANCE", "NSE")
quotes = facade.quotes([("RELIANCE", "NSE"), ("INFY", "NSE")])
chain = facade.option_chain("NIFTY", "NFO")

# orders
from app.integration.models import OrderRequest, Side, Product
resp = facade.place_order(OrderRequest(
    symbol="RELIANCE", exchange="NSE", side=Side.BUY,
    quantity=10, product=Product.MIS,
))
facade.cancel_order(resp.order_id)
ob = facade.orderbook()

# positions + portfolio
positions = facade.positions()
funds = facade.funds()
holdings = facade.holdings()

# paper trading
paper = facade.place_paper_order(request)

# broker status
status = facade.broker_status()
assert status.reachable

# websocket (async)
import asyncio
async def stream():
    await facade.ws_connect()
    await facade.ws_subscribe([("RELIANCE", "NSE")])
    async for tick in facade.ws_stream():
        print(tick.symbol, tick.ltp)
asyncio.run(stream())

# configuration
facade.set_config("analyze_mode", "true")
cfg = facade.list_config()
```

### From an API router

The integration router (`app/api/v1/integration.py`) exposes `GET /api/v1/integration/openalgo/status` which delegates to `facade.broker_status()`. Additional endpoints can be added by injecting `get_container().integration` and calling facade methods.

## Replacing OpenAlgo with another backend

1. **Implement the protocols.** Create a new adapter package (e.g. `app/integration/adapters/kite/`) with classes implementing the `Protocol`s in `interfaces.py`. Each class maps the new backend's responses into the neutral models from `models.py`.

2. **Build an adapter set.** Create a factory function (like `build_openalgo_adapters`) that constructs your adapters with a shared HTTP transport and cache.

3. **Wire the facade.** In `app/core/container.py`, add a branch that selects your backend based on a setting (e.g. `QUANTGPT_BACKEND=kite`). Construct `IntegrationFacade` with your adapter set.

4. **No other changes.** Because all callers use the facade and the neutral interfaces, nothing else needs to change.

Example skeleton:

```python
# app/integration/adapters/kite/factory.py
def build_kite_adapters(settings) -> KiteAdapterSet:
    transport = HttpTransport(base_url=settings.kite_base_url, ...)
    cache = TTLCache(default_ttl=settings.openalgo_cache_ttl_seconds)
    return KiteAdapterSet(
        market_data=KiteMarketDataAdapter(transport=transport, ...),
        orders=KiteOrdersAdapter(transport=transport, ...),
        # ...
    )

# app/core/container.py
def build_container() -> Container:
    s = get_settings()
    if s.quantgpt_backend == "kite":
        from app.integration.adapters.kite.factory import build_kite_adapters
        return Container(settings=s, integration=IntegrationFacade(build_kite_adapters(s), websocket_url=s.kite_ws_url))
    return Container(settings=s, integration=IntegrationFacade.from_settings(s))
```

## Testing

All adapters are tested with a `FakeHttp` transport that records calls and returns canned responses — no real OpenAlgo instance required.

```bash
# from backend/
pytest tests/ -v
```

Test coverage:

| Test file | Covers |
|---|---|
| `test_models.py` | neutral models, frozen, enums, exception hierarchy |
| `test_cache.py` | TTLCache get/set/invalidate/expiry/clear |
| `test_http_transport.py` | HTTP error translation (401/404/429/400/500/timeout/unreachable/invalid JSON) |
| `test_market_data_adapter.py` | quotes, multiquotes, depth, history, search, option chain, error envelope, caching |
| `test_orders_adapter.py` | place (market + limit), modify, cancel, orderbook, order status |
| `test_trades_adapter.py` | tradebook, trades for order |
| `test_positions_adapter.py` | positions, close position |
| `test_portfolio_adapter.py` | holdings, funds |
| `test_paper_trading_adapter.py` | paper order (analyze flag), paper positions, paper funds |
| `test_broker_status_adapter.py` | ping success/failure, status |
| `test_configuration_adapter.py` | get/set/list config, error handling |
| `test_websocket_adapter.py` | connect, auth success/failure/timeout, subscribe, tick parsing |
| `test_facade.py` | facade delegation, broker status ws url, paper routing, cache clear |

62 tests, all passing.

## Configuration

Environment variables (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `OPENALGO_BASE_URL` | `http://openalgo:5000` | OpenAlgo REST base URL |
| `OPENALGO_API_KEY` | (empty) | API key sent in request bodies |
| `OPENALGO_WEBSOCKET_URL` | `ws://openalgo:8765` | OpenAlgo WS proxy URL |
| `OPENALGO_REQUEST_TIMEOUT_SECONDS` | `10` | HTTP timeout |
| `OPENALGO_MAX_RETRIES` | `3` | retry attempts for transient errors |
| `OPENALGO_CACHE_TTL_SECONDS` | `30` | market-data cache TTL |
