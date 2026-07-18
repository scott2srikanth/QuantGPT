"""Pydantic schemas for the Strategy Research Engine API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrategyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    display_name: str
    type: str
    version: str
    description: str
    config_schema: dict[str, Any] = Field(default_factory=dict)
    default_config: dict[str, Any] = Field(default_factory=dict)
    is_plugin: bool = False
    source: str = "builtin"


class StrategyListOut(BaseModel):
    strategies: list[StrategyOut]
    count: int


class SignalOut(BaseModel):
    strategy_name: str
    symbol: str
    exchange: str = "NSE"
    signal_type: str
    strength: float
    price: float | None = None
    timestamp: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GenerateSignalsRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"
    interval: str = "1d"
    config: dict[str, Any] = Field(default_factory=dict)
    limit: int = 200


class GenerateSignalsResponse(BaseModel):
    strategy_name: str
    symbol: str
    signals: list[SignalOut]
    signal_count: int


class BacktestRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"
    interval: str = "1d"
    config: dict[str, Any] = Field(default_factory=dict)
    initial_capital: float = 100000.0
    limit: int = 365


class BacktestResultOut(BaseModel):
    strategy_name: str
    strategy_version: str
    symbol: str
    exchange: str = "NSE"
    config: dict[str, Any] = Field(default_factory=dict)
    start_date: str | None = None
    end_date: str | None = None
    initial_capital: float = 100000.0
    final_value: float = 0.0
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    benchmark_return: float = 0.0
    benchmark_sharpe: float = 0.0
    outperformance: float = 0.0
    equity_curve: list[dict[str, Any]] = Field(default_factory=list)
    trade_history: list[dict[str, Any]] = Field(default_factory=list)
    signals: list[dict[str, Any]] = Field(default_factory=list)


class MarketplaceListingOut(BaseModel):
    id: str
    strategy_name: str
    title: str
    description: str
    author: str
    tags: list[str] = Field(default_factory=list)
    rating: float = 0.0
    downloads: int = 0
    is_featured: bool = False
    is_published: bool = False
    strategy_info: dict[str, Any] | None = None


class PublishRequest(BaseModel):
    title: str | None = None
    description: str = ""
    author: str = ""
    tags: list[str] = Field(default_factory=list)


class RateRequest(BaseModel):
    rating: float = Field(ge=0, le=5)


class PluginLoadRequest(BaseModel):
    module_path: str | None = None
    file_path: str | None = None


class PluginLoadResponse(BaseModel):
    loaded: bool
    strategy_name: str | None = None
    error: str | None = None
