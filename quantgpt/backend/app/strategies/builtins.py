"""Built-in strategies for the Strategy Research Engine.

Seven strategies, each producing signals, configurable, versioned,
backtestable, and benchmarked:
  1. Momentum
  2. Breakout
  3. Swing
  4. Trend Following
  5. Mean Reversion
  6. Volatility Expansion
  7. Portfolio Rotation

No live trading — intelligence only.
"""

from __future__ import annotations

import math
from typing import Any

from app.analysis import indicators as ind
from app.integration.models import Candle
from app.strategies.base import Signal, SignalType, StrategyBase


# ────────────────────────── 1. Momentum ──────────────────────────

class MomentumStrategy(StrategyBase):
    """Momentum strategy: buy when short EMA > long EMA and RSI is in
    bullish zone (50-70). Sell when short EMA crosses below long EMA or
    RSI turns bearish."""

    name = "momentum"
    display_name = "Momentum"
    type = "momentum"
    version = "1.0.0"
    description = "EMA crossover + RSI momentum confirmation"

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "fast_ema": {"type": "integer", "default": 9, "description": "Fast EMA period"},
                "slow_ema": {"type": "integer", "default": 21, "description": "Slow EMA period"},
                "rsi_period": {"type": "integer", "default": 14, "description": "RSI period"},
                "rsi_buy": {"type": "number", "default": 50, "description": "RSI above this = bullish"},
                "rsi_sell": {"type": "number", "default": 45, "description": "RSI below this = bearish"},
            },
        }

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {"fast_ema": 9, "slow_ema": 21, "rsi_period": 14, "rsi_buy": 50, "rsi_sell": 45}

    def generate_signals(self, candles: list[Candle], config: dict[str, Any] | None = None) -> list[Signal]:
        cfg = {**self.default_config(), **(config or {})}
        if len(candles) < cfg["slow_ema"] + 5:
            return []

        closes = [float(c.close) for c in candles]
        fast = ind.ema(closes, cfg["fast_ema"])
        slow = ind.ema(closes, cfg["slow_ema"])
        rsi_series = ind.rsi_series(candles, cfg["rsi_period"])

        signals: list[Signal] = []
        for i in range(cfg["slow_ema"], len(candles)):
            if i >= len(fast) or i >= len(slow):
                continue
            rsi = rsi_series[i - 1] if (i - 1) < len(rsi_series) and not math.isnan(rsi_series[i - 1]) else None
            if rsi is None:
                continue

            c = candles[i]
            ts = str(c.timestamp)

            # Golden cross + RSI bullish
            if fast[i] > slow[i] and fast[i - 1] <= slow[i - 1] and rsi > cfg["rsi_buy"]:
                signals.append(Signal(
                    strategy_name=self.name, symbol="", signal_type=SignalType.BUY,
                    strength=min(60 + (rsi - 50) * 2, 100), price=float(c.close),
                    timestamp=ts, metadata={"ema_fast": fast[i], "ema_slow": slow[i], "rsi": rsi},
                ))
            # Death cross + RSI bearish
            elif fast[i] < slow[i] and fast[i - 1] >= slow[i - 1] and rsi < cfg["rsi_sell"]:
                signals.append(Signal(
                    strategy_name=self.name, symbol="", signal_type=SignalType.SELL,
                    strength=min(60 + (50 - rsi) * 2, 100), price=float(c.close),
                    timestamp=ts, metadata={"ema_fast": fast[i], "ema_slow": slow[i], "rsi": rsi},
                ))

        return signals


# ────────────────────────── 2. Breakout ──────────────────────────

class BreakoutStrategy(StrategyBase):
    """Breakout strategy: buy when price breaks above Donchian upper
    channel, sell when it breaks below the lower channel."""

    name = "breakout"
    display_name = "Breakout"
    type = "breakout"
    version = "1.0.0"
    description = "Donchian channel breakout — price exceeds N-period high/low"

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "period": {"type": "integer", "default": 20, "description": "Donchian channel period"},
                "volume_multiplier": {"type": "number", "default": 1.5, "description": "Volume must be N× average"},
            },
        }

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {"period": 20, "volume_multiplier": 1.5}

    def generate_signals(self, candles: list[Candle], config: dict[str, Any] | None = None) -> list[Signal]:
        cfg = {**self.default_config(), **(config or {})}
        period = cfg["period"]
        if len(candles) < period + 1:
            return []

        signals: list[Signal] = []
        for i in range(period, len(candles)):
            window = candles[i - period : i]
            hh = max(float(c.high) for c in window)
            ll = min(float(c.low) for c in window)
            close = float(candles[i].close)
            ts = str(candles[i].timestamp)

            # Volume confirmation
            vols = [float(c.volume) if c.volume else 0 for c in window]
            avg_vol = sum(vols) / len(vols) if vols else 0
            curr_vol = float(candles[i].volume) if candles[i].volume else 0
            vol_ok = curr_vol > avg_vol * cfg["volume_multiplier"] if avg_vol > 0 else True

            if close > hh and vol_ok:
                signals.append(Signal(
                    strategy_name=self.name, symbol="", signal_type=SignalType.BUY,
                    strength=80, price=close, timestamp=ts,
                    metadata={"breakout_level": hh, "volume_ratio": curr_vol / avg_vol if avg_vol > 0 else 0},
                ))
            elif close < ll and vol_ok:
                signals.append(Signal(
                    strategy_name=self.name, symbol="", signal_type=SignalType.SELL,
                    strength=80, price=close, timestamp=ts,
                    metadata={"breakdown_level": ll, "volume_ratio": curr_vol / avg_vol if avg_vol > 0 else 0},
                ))

        return signals


# ────────────────────────── 3. Swing ──────────────────────────

class SwingStrategy(StrategyBase):
    """Swing strategy: buy at oversold RSI + bullish MACD crossover,
    sell at overbought RSI + bearish MACD crossover. Captures short-term
    swings within a trend."""

    name = "swing"
    display_name = "Swing"
    type = "swing"
    version = "1.0.0"
    description = "RSI oversold/overbought + MACD crossover for swing entries/exits"

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "rsi_period": {"type": "integer", "default": 14},
                "rsi_oversold": {"type": "number", "default": 30},
                "rsi_overbought": {"type": "number", "default": 70},
                "macd_fast": {"type": "integer", "default": 12},
                "macd_slow": {"type": "integer", "default": 26},
                "macd_signal": {"type": "integer", "default": 9},
            },
        }

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {"rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70,
                "macd_fast": 12, "macd_slow": 26, "macd_signal": 9}

    def generate_signals(self, candles: list[Candle], config: dict[str, Any] | None = None) -> list[Signal]:
        cfg = {**self.default_config(), **(config or {})}
        if len(candles) < cfg["macd_slow"] + cfg["macd_signal"]:
            return []

        rsi_series = ind.rsi_series(candles, cfg["rsi_period"])
        macd_data = ind.macd(candles, cfg["macd_fast"], cfg["macd_slow"], cfg["macd_signal"])
        macd_line = macd_data.get("macd_series", [])
        signal_line = macd_data.get("signal_series", [])

        signals: list[Signal] = []
        offset = cfg["macd_slow"]
        for i in range(offset, len(candles)):
            rsi_idx = i - 1
            if rsi_idx >= len(rsi_series) or rsi_idx < 0:
                continue
            rsi = rsi_series[rsi_idx]
            if math.isnan(rsi):
                continue
            if i >= len(macd_line) or i >= len(signal_line):
                continue

            ts = str(candles[i].timestamp)
            close = float(candles[i].close)

            # Buy: RSI oversold + MACD bullish crossover
            if rsi < cfg["rsi_oversold"] and macd_line[i] > signal_line[i] and macd_line[i - 1] <= signal_line[i - 1]:
                signals.append(Signal(
                    strategy_name=self.name, symbol="", signal_type=SignalType.BUY,
                    strength=75, price=close, timestamp=ts,
                    metadata={"rsi": rsi, "macd": macd_line[i]},
                ))
            # Sell: RSI overbought + MACD bearish crossover
            elif rsi > cfg["rsi_overbought"] and macd_line[i] < signal_line[i] and macd_line[i - 1] >= signal_line[i - 1]:
                signals.append(Signal(
                    strategy_name=self.name, symbol="", signal_type=SignalType.SELL,
                    strength=75, price=close, timestamp=ts,
                    metadata={"rsi": rsi, "macd": macd_line[i]},
                ))

        return signals


# ────────────────────────── 4. Trend Following ──────────────────────────

class TrendFollowingStrategy(StrategyBase):
    """Trend following: uses Supertrend + ADX for strong trend confirmation.
    Buy when Supertrend flips up and ADX > 25. Sell when Supertrend flips down."""

    name = "trend_following"
    display_name = "Trend Following"
    type = "trend_following"
    version = "1.0.0"
    description = "Supertrend + ADX trend confirmation for sustained directional moves"

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "supertrend_period": {"type": "integer", "default": 10},
                "supertrend_multiplier": {"type": "number", "default": 3.0},
                "adx_period": {"type": "integer", "default": 14},
                "adx_threshold": {"type": "number", "default": 25, "description": "Minimum ADX for trend strength"},
            },
        }

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {"supertrend_period": 10, "supertrend_multiplier": 3.0,
                "adx_period": 14, "adx_threshold": 25}

    def generate_signals(self, candles: list[Candle], config: dict[str, Any] | None = None) -> list[Signal]:
        cfg = {**self.default_config(), **(config or {})}
        if len(candles) < cfg["supertrend_period"] + cfg["adx_period"]:
            return []

        signals: list[Signal] = []
        prev_trend = None

        for i in range(cfg["supertrend_period"] + 1, len(candles)):
            window = candles[: i + 1]
            st = ind.supertrend(window, cfg["supertrend_period"], cfg["supertrend_multiplier"])
            adx_data = ind.adx(window, cfg["adx_period"])
            adx_val = adx_data.get("adx")

            trend = st.get("trend")
            ts = str(candles[i].timestamp)
            close = float(candles[i].close)

            if trend == "up" and prev_trend != "up" and adx_val and adx_val > cfg["adx_threshold"]:
                signals.append(Signal(
                    strategy_name=self.name, symbol="", signal_type=SignalType.BUY,
                    strength=min(60 + (adx_val - 25) * 2, 100), price=close, timestamp=ts,
                    metadata={"supertrend": "up", "adx": adx_val},
                ))
            elif trend == "down" and prev_trend != "down" and adx_val and adx_val > cfg["adx_threshold"]:
                signals.append(Signal(
                    strategy_name=self.name, symbol="", signal_type=SignalType.SELL,
                    strength=min(60 + (adx_val - 25) * 2, 100), price=close, timestamp=ts,
                    metadata={"supertrend": "down", "adx": adx_val},
                ))

            prev_trend = trend

        return signals


# ────────────────────────── 5. Mean Reversion ──────────────────────────

class MeanReversionStrategy(StrategyBase):
    """Mean reversion: buy when price is below lower Bollinger Band and
    RSI is oversold (expecting reversion to mean). Sell when price is
    above upper Bollinger Band and RSI is overbought."""

    name = "mean_reversion"
    display_name = "Mean Reversion"
    type = "mean_reversion"
    version = "1.0.0"
    description = "Bollinger Bands + RSI for mean-reversion entries/exits"

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "bb_period": {"type": "integer", "default": 20},
                "bb_std": {"type": "number", "default": 2.0},
                "rsi_period": {"type": "integer", "default": 14},
                "rsi_oversold": {"type": "number", "default": 30},
                "rsi_overbought": {"type": "number", "default": 70},
            },
        }

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {"bb_period": 20, "bb_std": 2.0, "rsi_period": 14,
                "rsi_oversold": 30, "rsi_overbought": 70}

    def generate_signals(self, candles: list[Candle], config: dict[str, Any] | None = None) -> list[Signal]:
        cfg = {**self.default_config(), **(config or {})}
        if len(candles) < cfg["bb_period"] + 5:
            return []

        rsi_series = ind.rsi_series(candles, cfg["rsi_period"])
        signals: list[Signal] = []

        for i in range(cfg["bb_period"], len(candles)):
            window = candles[: i + 1]
            bb = ind.bollinger_bands(window, cfg["bb_period"], cfg["bb_std"])
            rsi_idx = i - 1
            if rsi_idx >= len(rsi_series) or rsi_idx < 0:
                continue
            rsi = rsi_series[rsi_idx]
            if math.isnan(rsi):
                continue

            close = float(candles[i].close)
            ts = str(candles[i].timestamp)
            lower = bb.get("lower")
            upper = bb.get("upper")

            if lower and close < lower and rsi < cfg["rsi_oversold"]:
                signals.append(Signal(
                    strategy_name=self.name, symbol="", signal_type=SignalType.BUY,
                    strength=70, price=close, timestamp=ts,
                    metadata={"bb_lower": lower, "rsi": rsi},
                ))
            elif upper and close > upper and rsi > cfg["rsi_overbought"]:
                signals.append(Signal(
                    strategy_name=self.name, symbol="", signal_type=SignalType.SELL,
                    strength=70, price=close, timestamp=ts,
                    metadata={"bb_upper": upper, "rsi": rsi},
                ))

        return signals


# ────────────────────────── 6. Volatility Expansion ──────────────────────────

class VolatilityExpansionStrategy(StrategyBase):
    """Volatility expansion: detect when ATR is expanding (ATR > SMA(ATR))
    combined with a Bollinger Band squeeze release. Buy/sell on the
    direction of the breakout after the squeeze."""

    name = "volatility_expansion"
    display_name = "Volatility Expansion"
    type = "volatility_expansion"
    version = "1.0.0"
    description = "ATR expansion + Bollinger Band squeeze release for volatility breakouts"

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "atr_period": {"type": "integer", "default": 14},
                "atr_sma_period": {"type": "integer", "default": 10, "description": "SMA period for ATR"},
                "bb_period": {"type": "integer", "default": 20},
                "bb_std": {"type": "number", "default": 2.0},
                "squeeze_threshold": {"type": "number", "default": 0.02, "description": "BB width threshold for squeeze"},
            },
        }

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {"atr_period": 14, "atr_sma_period": 10, "bb_period": 20,
                "bb_std": 2.0, "squeeze_threshold": 0.02}

    def generate_signals(self, candles: list[Candle], config: dict[str, Any] | None = None) -> list[Signal]:
        cfg = {**self.default_config(), **(config or {})}
        if len(candles) < cfg["bb_period"] + cfg["atr_period"]:
            return []

        signals: list[Signal] = []
        was_squeezed = False

        for i in range(cfg["bb_period"] + cfg["atr_period"], len(candles)):
            window = candles[: i + 1]
            atr_val = ind.atr(window, cfg["atr_period"])
            bb = ind.bollinger_bands(window, cfg["bb_period"], cfg["bb_std"])

            if atr_val is None or bb.get("width") is None:
                continue

            # ATR SMA
            atrs: list[float] = []
            for j in range(max(cfg["atr_sma_period"], 2), len(window)):
                a = ind.atr(window[: j + 1], cfg["atr_period"])
                if a is not None:
                    atrs.append(a)
            if len(atrs) < cfg["atr_sma_period"]:
                continue
            atr_sma = sum(atrs[-cfg["atr_sma_period"] :]) / cfg["atr_sma_period"]

            bb_width = bb["width"] or 0
            is_squeezed = bb_width < cfg["squeeze_threshold"]
            close = float(candles[i].close)
            ts = str(candles[i].timestamp)

            # Detect squeeze release: was squeezed, now expanding
            if was_squeezed and not is_squeezed and atr_val > atr_sma:
                # Direction: compare close to BB middle
                bb_middle = bb.get("middle")
                if bb_middle and close > bb_middle:
                    signals.append(Signal(
                        strategy_name=self.name, symbol="", signal_type=SignalType.BUY,
                        strength=75, price=close, timestamp=ts,
                        metadata={"atr": atr_val, "atr_sma": atr_sma, "bb_width": bb_width},
                    ))
                elif bb_middle and close < bb_middle:
                    signals.append(Signal(
                        strategy_name=self.name, symbol="", signal_type=SignalType.SELL,
                        strength=75, price=close, timestamp=ts,
                        metadata={"atr": atr_val, "atr_sma": atr_sma, "bb_width": bb_width},
                    ))

            was_squeezed = is_squeezed

        return signals


# ────────────────────────── 7. Portfolio Rotation ──────────────────────────

class PortfolioRotationStrategy(StrategyBase):
    """Portfolio rotation: evaluates multiple symbols and rotates into
    the strongest based on momentum + relative strength. Produces BUY
    signals for top N symbols and SELL for bottom N.

    Note: this strategy operates on a basket of symbols. When called
    with a single symbol's candles, it generates signals for that symbol
    based on its relative ranking in the basket (passed via config)."""

    name = "portfolio_rotation"
    display_name = "Portfolio Rotation"
    type = "portfolio_rotation"
    version = "1.0.0"
    description = "Rotate into strongest symbols by momentum + relative strength"

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "lookback": {"type": "integer", "default": 20, "description": "Momentum lookback period"},
                "top_n": {"type": "integer", "default": 3, "description": "Number of top symbols to buy"},
                "rotation_threshold": {"type": "number", "default": 0, "description": "Min return % to qualify"},
            },
        }

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {"lookback": 20, "top_n": 3, "rotation_threshold": 0}

    def generate_signals(self, candles: list[Candle], config: dict[str, Any] | None = None) -> list[Signal]:
        cfg = {**self.default_config(), **(config or {})}
        if len(candles) < cfg["lookback"] + 1:
            return []

        closes = [float(c.close) for c in candles]
        # Compute momentum over lookback period
        ret = ((closes[-1] / closes[-cfg["lookback"]]) - 1) * 100 if closes[-cfg["lookback"]] > 0 else 0

        # RSI for confirmation
        rsi = ind.rsi(candles, 14)

        signals: list[Signal] = []

        # If this symbol's return exceeds threshold, generate BUY
        if ret > cfg["rotation_threshold"]:
            strength = min(50 + abs(ret) * 3, 100)
            if rsi and rsi > 50:
                strength = min(strength + 10, 100)
            signals.append(Signal(
                strategy_name=self.name, symbol="", signal_type=SignalType.BUY,
                strength=strength, price=closes[-1],
                timestamp=str(candles[-1].timestamp),
                metadata={"momentum_return": ret, "lookback": cfg["lookback"], "rsi": rsi},
            ))
        elif ret < -abs(cfg["rotation_threshold"]):
            signals.append(Signal(
                strategy_name=self.name, symbol="", signal_type=SignalType.SELL,
                strength=min(50 + abs(ret) * 3, 100), price=closes[-1],
                timestamp=str(candles[-1].timestamp),
                metadata={"momentum_return": ret, "lookback": cfg["lookback"], "rsi": rsi},
            ))

        return signals


# ────────────────────────── Registry ──────────────────────────

BUILTIN_STRATEGIES: list[type[StrategyBase]] = [
    MomentumStrategy,
    BreakoutStrategy,
    SwingStrategy,
    TrendFollowingStrategy,
    MeanReversionStrategy,
    VolatilityExpansionStrategy,
    PortfolioRotationStrategy,
]

BUILTIN_STRATEGY_MAP: dict[str, type[StrategyBase]] = {
    cls.name: cls for cls in BUILTIN_STRATEGIES
}
