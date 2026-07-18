"""Technical indicators — pure functions.

All functions accept either list[float] closes or list[Candle]. They return
either a single value (latest), a list/series aligned to the input, or a
dict with named components.

No trading — intelligence only.
"""

from __future__ import annotations

import math
from typing import Any

from app.integration.models import Candle


# ── SMA ──

def sma(values: list[float], period: int) -> list[float]:
    """Simple moving average. Returns a series aligned to input length
    (NaN where insufficient data)."""
    out = [float("nan")] * len(values)
    if period <= 0 or len(values) < period:
        return out
    running = 0.0
    for i, v in enumerate(values):
        running += v
        if i >= period:
            running -= values[i - period]
        if i >= period - 1:
            out[i] = running / period
    return out


def sma_value(values: list[float], period: int) -> float | None:
    """Latest SMA value, or None if insufficient data."""
    if len(values) < period or period <= 0:
        return None
    return sum(values[-period:]) / period


# ── EMA ──

def ema(values: list[float], period: int) -> list[float]:
    """Exponential moving average. Returns a series aligned to input length."""
    out = [float("nan")] * len(values)
    if period <= 0 or len(values) == 0:
        return out
    k = 2.0 / (period + 1)
    ema_prev = values[0]
    out[0] = ema_prev
    for i in range(1, len(values)):
        ema_prev = values[i] * k + ema_prev * (1 - k)
        out[i] = ema_prev
    return out


def ema_value(values: list[float], period: int) -> float | None:
    if len(values) < period or period <= 0:
        return None
    return ema(values, period)[-1]


# ── RSI ──

def rsi_series(candles: list[Candle], period: int = 14) -> list[float]:
    """RSI as a series aligned to candles length. Uses close prices."""
    closes = [float(c.close) for c in candles]
    out = [float("nan")] * len(closes)
    if period <= 0 or len(closes) <= period:
        return out

    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        change = closes[i] - closes[i - 1]
        if change >= 0:
            gains += change
        else:
            losses -= change
    avg_gain = gains / period
    avg_loss = losses / period
    rs = avg_gain / avg_loss if avg_loss > 0 else float("inf")
    out[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period + 1, len(closes)):
        change = closes[i] - closes[i - 1]
        gain = change if change >= 0 else 0.0
        loss = -change if change < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        rs = avg_gain / avg_loss if avg_loss > 0 else float("inf")
        out[i] = 100.0 - (100.0 / (1.0 + rs))
    return out


def rsi(candles: list[Candle], period: int = 14) -> float | None:
    """Latest RSI value, or None if insufficient data."""
    series = rsi_series(candles, period)
    for v in reversed(series):
        if not math.isnan(v):
            return v
    return None


# ── MACD ──

def macd(
    candles: list[Candle],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, Any]:
    """MACD. Returns dict with macd_series, signal_series, histogram_series,
    and latest macd, signal, histogram values."""
    closes = [float(c.close) for c in candles]
    if len(closes) < slow + signal:
        return {
            "macd_series": [],
            "signal_series": [],
            "histogram_series": [],
            "macd": None,
            "signal": None,
            "histogram": None,
        }

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    # Replace NaN with 0 for signal computation
    macd_clean = [0.0 if math.isnan(v) else v for v in macd_line]
    signal_line = ema(macd_clean, signal)
    histogram = [m - s for m, s in zip(macd_clean, signal_line)]

    return {
        "macd_series": macd_clean,
        "signal_series": signal_line,
        "histogram_series": histogram,
        "macd": macd_clean[-1] if macd_clean else None,
        "signal": signal_line[-1] if signal_line else None,
        "histogram": histogram[-1] if histogram else None,
    }


# ── ADX ──

def adx(candles: list[Candle], period: int = 14) -> dict[str, Any]:
    """Average Directional Index. Returns dict with adx, plus_di, minus_di."""
    if len(candles) < period * 2:
        return {"adx": None, "plus_di": None, "minus_di": None}

    highs = [float(c.high) for c in candles]
    lows = [float(c.low) for c in candles]
    closes = [float(c.close) for c in candles]

    plus_dm = [0.0] * len(candles)
    minus_dm = [0.0] * len(candles)
    tr = [0.0] * len(candles)

    for i in range(1, len(candles)):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        plus_dm[i] = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm[i] = down_move if (down_move > up_move and down_move > 0) else 0.0
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )

    # Wilder's smoothing
    atr_s = [0.0] * len(candles)
    plus_s = [0.0] * len(candles)
    minus_s = [0.0] * len(candles)
    if len(tr) <= period:
        return {"adx": None, "plus_di": None, "minus_di": None}
    atr_s[period] = sum(tr[1 : period + 1])
    plus_s[period] = sum(plus_dm[1 : period + 1])
    minus_s[period] = sum(minus_dm[1 : period + 1])
    for i in range(period + 1, len(candles)):
        atr_s[i] = atr_s[i - 1] - (atr_s[i - 1] / period) + tr[i]
        plus_s[i] = plus_s[i - 1] - (plus_s[i - 1] / period) + plus_dm[i]
        minus_s[i] = minus_s[i - 1] - (minus_s[i - 1] / period) + minus_dm[i]

    plus_di = [0.0] * len(candles)
    minus_di = [0.0] * len(candles)
    dx = [0.0] * len(candles)
    for i in range(period, len(candles)):
        plus_di[i] = (plus_s[i] / atr_s[i] * 100.0) if atr_s[i] > 0 else 0.0
        minus_di[i] = (minus_s[i] / atr_s[i] * 100.0) if atr_s[i] > 0 else 0.0
        di_sum = plus_di[i] + minus_di[i]
        dx[i] = (abs(plus_di[i] - minus_di[i]) / di_sum * 100.0) if di_sum > 0 else 0.0

    # ADX = smoothed DX
    adx_val = None
    if len(dx) >= 2 * period:
        adx_val = sum(dx[period : 2 * period]) / period
        for i in range(2 * period, len(dx)):
            adx_val = (adx_val * (period - 1) + dx[i]) / period

    return {
        "adx": adx_val,
        "plus_di": plus_di[-1] if plus_di else None,
        "minus_di": minus_di[-1] if minus_di else None,
    }


# ── ATR ──

def atr(candles: list[Candle], period: int = 14) -> float | None:
    """Average True Range (latest value)."""
    if len(candles) < period + 1:
        return None
    trs: list[float] = []
    for i in range(1, len(candles)):
        h = float(candles[i].high)
        l = float(candles[i].low)
        pc = float(candles[i - 1].close)
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    # Wilder's smoothing
    atr_val = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr_val = (atr_val * (period - 1) + tr) / period
    return atr_val


def atr_series(candles: list[Candle], period: int = 14) -> list[float]:
    """ATR as a series aligned to candles length."""
    out = [float("nan")] * len(candles)
    if len(candles) < period + 1:
        return out
    trs = [0.0] * len(candles)
    for i in range(1, len(candles)):
        h = float(candles[i].high)
        l = float(candles[i].low)
        pc = float(candles[i - 1].close)
        trs[i] = max(h - l, abs(h - pc), abs(l - pc))
    atr_val = sum(trs[1 : period + 1]) / period
    out[period] = atr_val
    for i in range(period + 1, len(candles)):
        atr_val = (atr_val * (period - 1) + trs[i]) / period
        out[i] = atr_val
    return out


# ── VWAP ──

def vwap(candles: list[Candle]) -> float | None:
    """Volume-weighted average price over the given candles."""
    pv = 0.0
    vol = 0.0
    for c in candles:
        typical = (float(c.high) + float(c.low) + float(c.close)) / 3.0
        v = float(c.volume) if c.volume else 0
        pv += typical * v
        vol += v
    return (pv / vol) if vol > 0 else None


def vwap_series(candles: list[Candle]) -> list[float]:
    """Cumulative VWAP as a series."""
    out = [float("nan")] * len(candles)
    pv = 0.0
    vol = 0.0
    for i, c in enumerate(candles):
        typical = (float(c.high) + float(c.low) + float(c.close)) / 3.0
        v = float(c.volume) if c.volume else 0
        pv += typical * v
        vol += v
        out[i] = (pv / vol) if vol > 0 else float("nan")
    return out


# ── Supertrend ──

def supertrend(
    candles: list[Candle],
    period: int = 10,
    multiplier: float = 3.0,
) -> dict[str, Any]:
    """Supertrend indicator. Returns dict with trend ('up'/'down'),
    value, upper_band, lower_band."""
    if len(candles) < period + 1:
        return {"trend": None, "value": None, "upper_band": None, "lower_band": None}

    atrs = atr_series(candles, period)
    closes = [float(c.close) for c in candles]
    highs = [float(c.high) for c in candles]
    lows = [float(c.low) for c in candles]

    final_upper = [float("nan")] * len(candles)
    final_lower = [float("nan")] * len(candles)
    trend = [None] * len(candles)
    supertrend_val = [float("nan")] * len(candles)

    for i in range(period, len(candles)):
        if math.isnan(atrs[i]):
            continue
        hl2 = (highs[i] + lows[i]) / 2.0
        basic_upper = hl2 + multiplier * atrs[i]
        basic_lower = hl2 - multiplier * atrs[i]

        # Final upper band
        if i > period and not math.isnan(final_upper[i - 1]):
            if basic_upper < final_upper[i - 1] or closes[i - 1] > final_upper[i - 1]:
                final_upper[i] = basic_upper
            else:
                final_upper[i] = final_upper[i - 1]
        else:
            final_upper[i] = basic_upper

        # Final lower band
        if i > period and not math.isnan(final_lower[i - 1]):
            if basic_lower > final_lower[i - 1] or closes[i - 1] < final_lower[i - 1]:
                final_lower[i] = basic_lower
            else:
                final_lower[i] = final_lower[i - 1]
        else:
            final_lower[i] = basic_lower

        # Trend determination
        if i > period:
            prev_trend = trend[i - 1]
            if prev_trend == "up":
                if closes[i] < final_lower[i]:
                    trend[i] = "down"
                else:
                    trend[i] = "up"
            elif prev_trend == "down":
                if closes[i] > final_upper[i]:
                    trend[i] = "up"
                else:
                    trend[i] = "down"
            else:
                trend[i] = "up" if closes[i] > final_upper[i] else "down"
        else:
            trend[i] = "up" if closes[i] > final_upper[i] else "down"

        supertrend_val[i] = final_lower[i] if trend[i] == "up" else final_upper[i]

    last = len(candles) - 1
    return {
        "trend": trend[last],
        "value": supertrend_val[last] if not math.isnan(supertrend_val[last]) else None,
        "upper_band": final_upper[last] if not math.isnan(final_upper[last]) else None,
        "lower_band": final_lower[last] if not math.isnan(final_lower[last]) else None,
    }


# ── Bollinger Bands ──

def bollinger_bands(
    candles: list[Candle],
    period: int = 20,
    std_dev: float = 2.0,
) -> dict[str, Any]:
    """Bollinger Bands. Returns dict with middle, upper, lower, width."""
    closes = [float(c.close) for c in candles]
    if len(closes) < period:
        return {"middle": None, "upper": None, "lower": None, "width": None}

    sma_vals = sma(closes, period)
    last_idx = len(closes) - 1
    if math.isnan(sma_vals[last_idx]):
        return {"middle": None, "upper": None, "lower": None, "width": None}

    window = closes[-period:]
    mean = sum(window) / period
    variance = sum((x - mean) ** 2 for x in window) / period
    std = math.sqrt(variance)
    upper = mean + std_dev * std
    lower = mean - std_dev * std
    width = (upper - lower) / mean if mean > 0 else 0.0

    return {"middle": mean, "upper": upper, "lower": lower, "width": width}


# ── Donchian Channel ──

def donchian_channel(
    candles: list[Candle],
    period: int = 20,
) -> dict[str, Any]:
    """Donchian channel. Returns dict with upper, lower, middle."""
    if len(candles) < period:
        return {"upper": None, "lower": None, "middle": None}
    window = candles[-period:]
    hh = max(float(c.high) for c in window)
    ll = min(float(c.low) for c in window)
    return {"upper": hh, "lower": ll, "middle": (hh + ll) / 2.0}


# ── Ichimoku ──

def ichimoku(
    candles: list[Candle],
    conversion_period: int = 9,
    base_period: int = 26,
    span_b_period: int = 52,
) -> dict[str, Any]:
    """Ichimoku Cloud. Returns dict with tenkan, kijun, senkou_a, senkou_b."""
    if len(candles) < span_b_period:
        return {"tenkan": None, "kijun": None, "senkou_a": None, "senkou_b": None}

    def midpoint(period: int) -> float | None:
        if len(candles) < period:
            return None
        w = candles[-period:]
        hh = max(float(c.high) for c in w)
        ll = min(float(c.low) for c in w)
        return (hh + ll) / 2.0

    tenkan = midpoint(conversion_period)
    kijun = midpoint(base_period)
    senkou_b = midpoint(span_b_period)
    senkou_a = (tenkan + kijun) / 2.0 if tenkan and kijun else None
    return {"tenkan": tenkan, "kijun": kijun, "senkou_a": senkou_a, "senkou_b": senkou_b}


# ── Stochastic ──

def stochastic(
    candles: list[Candle],
    k_period: int = 14,
    d_period: int = 3,
) -> dict[str, Any]:
    """Stochastic oscillator. Returns dict with k, d."""
    if len(candles) < k_period + d_period:
        return {"k": None, "d": None}
    ks: list[float] = []
    for i in range(k_period - 1, len(candles)):
        w = candles[i - k_period + 1 : i + 1]
        hh = max(float(c.high) for c in w)
        ll = min(float(c.low) for c in w)
        close = float(candles[i].close)
        k = ((close - ll) / (hh - ll) * 100.0) if hh > ll else 50.0
        ks.append(k)
    d = sum(ks[-d_period:]) / d_period if len(ks) >= d_period else None
    return {"k": ks[-1] if ks else None, "d": d}


# ── CCI ──

def cci(candles: list[Candle], period: int = 20) -> float | None:
    """Commodity Channel Index (latest)."""
    if len(candles) < period:
        return None
    tp = [(float(c.high) + float(c.low) + float(c.close)) / 3.0 for c in candles]
    window = tp[-period:]
    mean = sum(window) / period
    mean_dev = sum(abs(x - mean) for x in window) / period
    if mean_dev == 0:
        return 0.0
    return (tp[-1] - mean) / (0.015 * mean_dev)


# ── OBV ──

def obv(candles: list[Candle]) -> list[float]:
    """On-Balance Volume as a cumulative series."""
    out = [0.0] * len(candles)
    if not candles:
        return out
    for i in range(1, len(candles)):
        prev_close = float(candles[i - 1].close)
        curr_close = float(candles[i].close)
        vol = float(candles[i].volume) if candles[i].volume else 0
        if curr_close > prev_close:
            out[i] = out[i - 1] + vol
        elif curr_close < prev_close:
            out[i] = out[i - 1] - vol
        else:
            out[i] = out[i - 1]
    return out


# ── Aroon ──

def aroon(candles: list[Candle], period: int = 25) -> dict[str, Any]:
    """Aroon indicator. Returns dict with aroon_up, aroon_down, oscillator."""
    if len(candles) < period + 1:
        return {"aroon_up": None, "aroon_down": None, "oscillator": None}
    window = candles[-(period + 1) :]
    highs = [float(c.high) for c in window]
    lows = [float(c.low) for c in window]
    hh_idx = highs.index(max(highs))
    ll_idx = lows.index(min(lows))
    aroon_up = ((period - hh_idx) / period) * 100.0
    aroon_down = ((period - ll_idx) / period) * 100.0
    return {
        "aroon_up": aroon_up,
        "aroon_down": aroon_down,
        "oscillator": aroon_up - aroon_down,
    }


# ── Williams %R ──

def williams_r(candles: list[Candle], period: int = 14) -> float | None:
    """Williams %R (latest)."""
    if len(candles) < period:
        return None
    w = candles[-period:]
    hh = max(float(c.high) for c in w)
    ll = min(float(c.low) for c in w)
    close = float(candles[-1].close)
    if hh == ll:
        return -50.0
    return ((hh - close) / (hh - ll)) * -100.0


# ── Aggregator ──

def all_indicators(candles: list[Candle]) -> dict[str, Any]:
    """Compute all indicators for a candle series and return a flat dict."""
    closes = [float(c.close) for c in candles]
    return {
        "sma_20": sma_value(closes, 20),
        "sma_50": sma_value(closes, 50),
        "ema_9": ema_value(closes, 9),
        "ema_21": ema_value(closes, 21),
        "rsi_14": rsi(candles, 14),
        "macd": macd(candles),
        "adx": adx(candles, 14),
        "atr_14": atr(candles, 14),
        "vwap": vwap(candles),
        "supertrend": supertrend(candles),
        "bollinger_bands": bollinger_bands(candles),
        "donchian_channel": donchian_channel(candles),
        "ichimoku": ichimoku(candles),
        "stochastic": stochastic(candles),
        "cci": cci(candles, 20),
        "obv": obv(candles)[-1] if candles else None,
        "aroon": aroon(candles),
        "williams_r": williams_r(candles),
    }
