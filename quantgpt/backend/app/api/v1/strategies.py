"""API router for the Strategy Research Engine.

Endpoints:
  GET    /strategies                    — list all registered strategies
  GET    /strategies/{name}             — get strategy details
  POST   /strategies/{name}/signals     — generate signals for a symbol
  POST   /strategies/{name}/backtest     — run a backtest
  GET    /strategies/{name}/config       — get strategy config schema
  GET    /marketplace                    — list published strategies
  GET    /marketplace/{name}             — get a marketplace listing
  POST   /marketplace/{name}/publish     — publish a strategy
  POST   /marketplace/{name}/rate        — rate a strategy
  POST   /marketplace/{name}/download    — download a strategy
  POST   /marketplace/{name}/feature     — feature a strategy
  POST   /plugins/load                  — load a plugin strategy
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.strategies.marketplace import build_marketplace
from app.strategies.plugins import load_plugin_from_file, load_plugin_from_module
from app.strategies.registry import StrategyNotFoundError, build_registry
from app.strategies.schemas import (
    BacktestRequest,
    BacktestResultOut,
    GenerateSignalsRequest,
    GenerateSignalsResponse,
    MarketplaceListingOut,
    PluginLoadRequest,
    PluginLoadResponse,
    PublishRequest,
    RateRequest,
    SignalOut,
    StrategyListOut,
    StrategyOut,
)

router = APIRouter(prefix="/strategies", tags=["strategies"])


def _get_registry():
    return build_registry()


def _get_marketplace():
    return build_marketplace(_get_registry())


def _get_facade():
    """Get the integration facade for fetching candle data."""
    try:
        from app.core.container import get_container
        return get_container().integration
    except Exception:
        return None


# ── Strategy endpoints ──

@router.get("", response_model=StrategyListOut)
def list_strategies() -> StrategyListOut:
    registry = _get_registry()
    strategies = [StrategyOut(**s) for s in registry.list_all()]
    return StrategyListOut(strategies=strategies, count=len(strategies))


@router.get("/{name}", response_model=StrategyOut)
def get_strategy(name: str) -> StrategyOut:
    registry = _get_registry()
    try:
        strategy = registry.get(name)
    except StrategyNotFoundError:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
    return StrategyOut(**strategy.to_dict())


@router.get("/{name}/config")
def get_strategy_config(name: str) -> dict[str, Any]:
    registry = _get_registry()
    try:
        strategy = registry.get(name)
    except StrategyNotFoundError:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
    return {"schema": strategy.config_schema(), "defaults": strategy.default_config()}


@router.post("/{name}/signals", response_model=GenerateSignalsResponse)
def generate_signals(name: str, req: GenerateSignalsRequest) -> GenerateSignalsResponse:
    registry = _get_registry()
    try:
        strategy = registry.get(name)
    except StrategyNotFoundError:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")

    facade = _get_facade()
    if facade is None:
        raise HTTPException(status_code=503, detail="Market data facade not available")

    try:
        candles = facade.history(req.symbol, req.exchange, req.interval, limit=req.limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch history: {e}")

    signals = strategy.generate_signals(candles, req.config)
    return GenerateSignalsResponse(
        strategy_name=name,
        symbol=req.symbol,
        signals=[SignalOut(**s.model_dump()) for s in signals],
        signal_count=len(signals),
    )


@router.post("/{name}/backtest", response_model=BacktestResultOut)
def run_backtest(name: str, req: BacktestRequest) -> BacktestResultOut:
    registry = _get_registry()
    try:
        strategy = registry.get(name)
    except StrategyNotFoundError:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")

    facade = _get_facade()
    if facade is None:
        raise HTTPException(status_code=503, detail="Market data facade not available")

    try:
        candles = facade.history(req.symbol, req.exchange, req.interval, limit=req.limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch history: {e}")

    result = strategy.backtest(candles, req.config, initial_capital=req.initial_capital)
    return BacktestResultOut(**result.model_dump())


# ── Marketplace endpoints ──

marketplace_router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@marketplace_router.get("", response_model=list[MarketplaceListingOut])
def list_marketplace(*, tag: str | None = None, strategy_type: str | None = None) -> list[MarketplaceListingOut]:
    mp = _get_marketplace()
    listings = mp.list_published(tag=tag, strategy_type=strategy_type)
    return [MarketplaceListingOut(**l) for l in listings]


@marketplace_router.get("/{name}", response_model=MarketplaceListingOut)
def get_marketplace_listing(name: str) -> MarketplaceListingOut:
    mp = _get_marketplace()
    listing = mp.get_listing(name)
    if listing is None:
        raise HTTPException(status_code=404, detail=f"Listing for '{name}' not found")
    return MarketplaceListingOut(**listing)


@marketplace_router.post("/{name}/publish", response_model=MarketplaceListingOut)
def publish_strategy(name: str, req: PublishRequest) -> MarketplaceListingOut:
    registry = _get_registry()
    mp = _get_marketplace()
    try:
        strategy = registry.get(name)
    except StrategyNotFoundError:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
    listing = mp.publish(
        name,
        title=req.title or strategy.display_name,
        description=req.description or strategy.description,
        author=req.author,
        tags=req.tags or [strategy.type],
    )
    return MarketplaceListingOut(**listing.to_dict())


@marketplace_router.post("/{name}/rate", response_model=MarketplaceListingOut)
def rate_strategy(name: str, req: RateRequest) -> MarketplaceListingOut:
    mp = _get_marketplace()
    try:
        listing = mp.rate(name, req.rating)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Listing for '{name}' not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return MarketplaceListingOut(**listing.to_dict())


@marketplace_router.post("/{name}/download")
def download_strategy(name: str) -> dict[str, Any]:
    mp = _get_marketplace()
    try:
        return mp.download(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Listing for '{name}' not found")


@marketplace_router.post("/{name}/feature", response_model=MarketplaceListingOut)
def feature_strategy(name: str) -> MarketplaceListingOut:
    mp = _get_marketplace()
    try:
        listing = mp.feature(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Listing for '{name}' not found")
    return MarketplaceListingOut(**listing.to_dict())


# ── Plugin endpoints ──

plugins_router = APIRouter(prefix="/plugins", tags=["plugins"])


@plugins_router.post("/load", response_model=PluginLoadResponse)
def load_plugin(req: PluginLoadRequest) -> PluginLoadResponse:
    registry = _get_registry()
    if req.module_path:
        strategy = load_plugin_from_module(req.module_path, registry)
        if strategy:
            return PluginLoadResponse(loaded=True, strategy_name=strategy.name)
        return PluginLoadResponse(loaded=False, error="Failed to load plugin from module")
    elif req.file_path:
        strategy = load_plugin_from_file(req.file_path, registry)
        if strategy:
            return PluginLoadResponse(loaded=True, strategy_name=strategy.name)
        return PluginLoadResponse(loaded=False, error="Failed to load plugin from file")
    else:
        return PluginLoadResponse(loaded=False, error="Provide either module_path or file_path")
