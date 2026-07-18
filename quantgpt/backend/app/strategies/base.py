"""Strategy base class and signal types.

Every strategy extends StrategyBase and implements generate_signals().
Strategies are configurable, versioned, backtestable, and benchmarked.
No live trading — intelligence only.
"""

from __future__ import annotations

import abc
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.integration.models import Candle


class SignalType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class Signal(BaseModel):
    """A trading signal produced by a strategy. No execution — intelligence only."""
    model_config = ConfigDict(frozen=True)

    strategy_name: str
    symbol: str
    exchange: str = "NSE"
    signal_type: SignalType
    strength: float = Field(ge=0, le=100, description="0-100 confidence")
    price: float | None = None
    timestamp: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategyConfig(BaseModel):
    """Describes a strategy's configurable parameters."""
    model_config = ConfigDict(frozen=True)

    schema: dict[str, Any] = Field(default_factory=dict, description="JSON schema for config params")
    defaults: dict[str, Any] = Field(default_factory=dict, description="Default param values")


class BacktestTrade(BaseModel):
    """A single trade in a backtest."""
    model_config = ConfigDict(frozen=True)

    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    quantity: int = 1
    side: str = "long"
    pnl: float = 0.0
    pnl_percent: float = 0.0
    hold_days: int = 0


class BacktestResult(BaseModel):
    """Result of a backtest run, including benchmark comparison."""
    model_config = ConfigDict(frozen=False)

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
    # Benchmark (buy-and-hold)
    benchmark_return: float = 0.0
    benchmark_sharpe: float = 0.0
    outperformance: float = 0.0
    # Detailed data
    equity_curve: list[dict[str, Any]] = Field(default_factory=list)
    trade_history: list[dict[str, Any]] = Field(default_factory=list)
    signals: list[dict[str, Any]] = Field(default_factory=list)


class StrategyBase(abc.ABC):
    """Abstract base for all strategies.

    Concrete strategies set name, display_name, type, version, and
    implement generate_signals(). They declare their config via
    get_config() and can be backtested via backtest().
    """

    name: str = ""
    display_name: str = ""
    type: str = "custom"
    version: str = "1.0.0"
    description: str = ""

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        """Override to declare configurable parameters as a JSON schema."""
        return {}

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        """Override to provide default parameter values."""
        return {}

    @classmethod
    def get_config(cls) -> StrategyConfig:
        return StrategyConfig(schema=cls.config_schema(), defaults=cls.default_config())

    @abc.abstractmethod
    def generate_signals(
        self,
        candles: list[Candle],
        config: dict[str, Any] | None = None,
    ) -> list[Signal]:
        """Produce signals from candles. No trading — intelligence only."""
        ...

    def backtest(
        self,
        candles: list[Candle],
        config: dict[str, Any] | None = None,
        initial_capital: float = 100000.0,
    ) -> BacktestResult:
        """Run a backtest on historical candles. Uses the backtesting engine."""
        from app.strategies.backtester import Backtester
        bt = Backtester(strategy=self, config=config or self.default_config(), initial_capital=initial_capital)
        return bt.run(candles)

    def to_dict(self) -> dict[str, Any]:
        """Serializable representation for the registry/marketplace."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "type": self.type,
            "version": self.version,
            "description": self.description,
            "config_schema": self.config_schema(),
            "default_config": self.default_config(),
            "is_plugin": False,
            "source": "builtin",
        }
