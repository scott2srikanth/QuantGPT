"""Backtesting engine.

Runs a strategy over historical candles, simulates trades from signals,
and computes performance metrics. Always benchmarks against buy-and-hold.
No live trading — research only.
"""

from __future__ import annotations

import math
from typing import Any

from app.analysis import indicators as ind
from app.integration.models import Candle
from app.strategies.base import BacktestResult, BacktestTrade, Signal, SignalType


class Backtester:
    """Simulates a strategy on historical data and benchmarks vs buy-and-hold."""

    def __init__(
        self,
        *,
        strategy,
        config: dict[str, Any] | None = None,
        initial_capital: float = 100000.0,
    ) -> None:
        self._strategy = strategy
        self._config = config or strategy.default_config()
        self._initial_capital = initial_capital

    def run(self, candles: list[Candle]) -> BacktestResult:
        if len(candles) < 2:
            return self._empty_result()

        signals = self._strategy.generate_signals(candles, self._config)
        trades = self._simulate_trades(candles, signals)
        equity_curve = self._build_equity_curve(candles, trades)
        metrics = self._compute_metrics(trades, equity_curve)
        benchmark = self._benchmark(candles)

        result = BacktestResult(
            strategy_name=self._strategy.name,
            strategy_version=self._strategy.version,
            symbol=candles[0].symbol if hasattr(candles[0], "symbol") else "",
            config=self._config,
            start_date=str(candles[0].timestamp) if candles else None,
            end_date=str(candles[-1].timestamp) if candles else None,
            initial_capital=self._initial_capital,
            final_value=metrics["final_value"],
            total_return=metrics["total_return"],
            sharpe_ratio=metrics["sharpe_ratio"],
            max_drawdown=metrics["max_drawdown"],
            win_rate=metrics["win_rate"],
            total_trades=metrics["total_trades"],
            winning_trades=metrics["winning_trades"],
            losing_trades=metrics["losing_trades"],
            avg_win=metrics["avg_win"],
            avg_loss=metrics["avg_loss"],
            profit_factor=metrics["profit_factor"],
            benchmark_return=benchmark["return"],
            benchmark_sharpe=benchmark["sharpe"],
            outperformance=metrics["total_return"] - benchmark["return"],
            equity_curve=equity_curve,
            trade_history=[t.model_dump() for t in trades],
            signals=[s.model_dump() for s in signals],
        )
        return result

    def _simulate_trades(self, candles: list[Candle], signals: list[Signal]) -> list[BacktestTrade]:
        """Convert signals into simulated trades. A BUY signal opens a long
        position, a SELL signal closes it. HOLD does nothing."""
        trades: list[BacktestTrade] = []
        position_open = False
        entry_price = 0.0
        entry_idx = 0

        # Map signals to candle indices by timestamp
        signal_map: dict[str, Signal] = {}
        for s in signals:
            ts = s.timestamp or ""
            signal_map[ts] = s

        for i, c in enumerate(candles):
            ts = str(c.timestamp)
            sig = signal_map.get(ts)
            if sig is None:
                continue

            close = float(c.close)
            if sig.signal_type == SignalType.BUY and not position_open:
                entry_price = close
                entry_idx = i
                position_open = True
            elif sig.signal_type == SignalType.SELL and position_open:
                pnl = (close - entry_price) * 100   # per-unit * lot
                pnl_pct = ((close / entry_price) - 1) * 100 if entry_price > 0 else 0
                trades.append(BacktestTrade(
                    entry_date=str(candles[entry_idx].timestamp),
                    exit_date=ts,
                    entry_price=entry_price,
                    exit_price=close,
                    pnl=pnl,
                    pnl_percent=pnl_pct,
                    hold_days=i - entry_idx,
                ))
                position_open = False

        # Close any open position at the last candle
        if position_open and candles:
            last = candles[-1]
            close = float(last.close)
            pnl = (close - entry_price) * 100
            pnl_pct = ((close / entry_price) - 1) * 100 if entry_price > 0 else 0
            trades.append(BacktestTrade(
                entry_date=str(candles[entry_idx].timestamp),
                exit_date=str(last.timestamp),
                entry_price=entry_price,
                exit_price=close,
                pnl=pnl,
                pnl_percent=pnl_pct,
                hold_days=len(candles) - 1 - entry_idx,
            ))

        return trades

    def _build_equity_curve(self, candles: list[Candle], trades: list[BacktestTrade]) -> list[dict[str, Any]]:
        """Build equity curve from trades. Between trades, equity stays flat."""
        curve: list[dict[str, Any]] = []
        equity = self._initial_capital
        trade_idx = 0
        in_position = False
        entry_price = 0.0
        units = 0

        for i, c in enumerate(candles):
            close = float(c.close)
            # Check if a trade starts or ends at this candle
            if trade_idx < len(trades):
                t = trades[trade_idx]
                if str(c.timestamp) == t.entry_date:
                    in_position = True
                    entry_price = t.entry_price
                    units = int(equity / entry_price) if entry_price > 0 else 0
                    equity -= units * entry_price
                if str(c.timestamp) == t.exit_date and in_position:
                    equity += units * close
                    in_position = False
                    trade_idx += 1

            # Mark-to-market if in position
            mtm_equity = equity + (units * close) if in_position else equity
            curve.append({"date": str(c.timestamp), "value": round(mtm_equity, 2)})

        return curve

    def _compute_metrics(self, trades: list[BacktestTrade], equity_curve: list[dict[str, Any]]) -> dict[str, Any]:
        if not equity_curve:
            return self._empty_metrics()

        final_value = equity_curve[-1]["value"]
        total_return = ((final_value / self._initial_capital) - 1) * 100

        # Sharpe ratio from equity curve returns
        returns: list[float] = []
        for i in range(1, len(equity_curve)):
            prev = equity_curve[i - 1]["value"]
            curr = equity_curve[i]["value"]
            if prev > 0:
                returns.append((curr / prev) - 1)

        sharpe = 0.0
        if returns:
            avg_ret = sum(returns) / len(returns)
            std_ret = math.sqrt(sum((r - avg_ret) ** 2 for r in returns) / len(returns)) if len(returns) > 1 else 0
            sharpe = (avg_ret / std_ret * math.sqrt(252)) if std_ret > 0 else 0

        # Max drawdown
        peak = equity_curve[0]["value"]
        max_dd = 0.0
        for point in equity_curve:
            v = point["value"]
            if v > peak:
                peak = v
            dd = ((peak - v) / peak) * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        # Trade stats
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        total_trades = len(trades)
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
        avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t.pnl for t in losses) / len(losses) if losses else 0
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf") if gross_profit > 0 else 0

        return {
            "final_value": round(final_value, 2),
            "total_return": round(total_return, 2),
            "sharpe_ratio": round(sharpe, 4),
            "max_drawdown": round(max_dd, 2),
            "win_rate": round(win_rate, 2),
            "total_trades": total_trades,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else 999.0,
        }

    def _benchmark(self, candles: list[Candle]) -> dict[str, float]:
        """Buy-and-hold benchmark."""
        if len(candles) < 2:
            return {"return": 0.0, "sharpe": 0.0}

        prices = [float(c.close) for c in candles]
        ret = ((prices[-1] / prices[0]) - 1) * 100

        # Benchmark Sharpe
        rets = [(prices[i] / prices[i - 1] - 1) for i in range(1, len(prices)) if prices[i - 1] > 0]
        sharpe = 0.0
        if rets:
            avg = sum(rets) / len(rets)
            std = math.sqrt(sum((r - avg) ** 2 for r in rets) / len(rets)) if len(rets) > 1 else 0
            sharpe = (avg / std * math.sqrt(252)) if std > 0 else 0

        return {"return": round(ret, 2), "sharpe": round(sharpe, 4)}

    def _empty_result(self) -> BacktestResult:
        return BacktestResult(
            strategy_name=self._strategy.name,
            strategy_version=self._strategy.version,
            symbol="",
        )

    def _empty_metrics(self) -> dict[str, Any]:
        return {
            "final_value": self._initial_capital,
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0,
        }
