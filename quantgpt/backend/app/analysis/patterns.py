"""Pattern recognition module.

Detects candlestick and chart patterns from a list of candles. Returns
a list of detected patterns with confidence scores (0.0–1.0). Pure
functions, no side effects.
"""

from __future__ import annotations

from app.integration.models import Candle


def _body(c: Candle) -> float:
    return abs(float(c.close) - float(c.open))


def _upper_shadow(c: Candle) -> float:
    return float(c.high) - max(float(c.open), float(c.close))


def _lower_shadow(c: Candle) -> float:
    return min(float(c.open), float(c.close)) - float(c.low)


def _range(c: Candle) -> float:
    return float(c.high) - float(c.low)


def _is_bullish(c: Candle) -> bool:
    return float(c.close) > float(c.open)


def _is_bearish(c: Candle) -> bool:
    return float(c.close) < float(c.open)


# ────────────────────────── Single-candle patterns ──────────────────────────

def doji(candles: list[Candle]) -> dict[str, Any] | None:
    """Doji: open ≈ close (body < 10% of range)."""
    if not candles:
        return None
    c = candles[-1]
    r = _range(c)
    if r == 0:
        return None
    if _body(c) / r < 0.1:
        return {"pattern": "doji", "confidence": 0.8, "type": "neutral"}
    return None


def hammer(candles: list[Candle]) -> dict[str, Any] | None:
    """Hammer: small body at top, long lower shadow (>2x body), small upper shadow."""
    if len(candles) < 1:
        return None
    c = candles[-1]
    body = _body(c)
    if body == 0:
        return None
    ls = _lower_shadow(c)
    us = _upper_shadow(c)
    r = _range(c)
    if r == 0:
        return None
    # Lower shadow at least 2x body, upper shadow less than 10% of range
    if ls > 2.0 * body and us < 0.1 * r:
        return {"pattern": "hammer", "confidence": 0.75, "type": "bullish"}
    return None


def shooting_star(candles: list[Candle]) -> dict[str, Any] | None:
    """Shooting star: small body at bottom, long upper shadow, small lower shadow."""
    if len(candles) < 1:
        return None
    c = candles[-1]
    body = _body(c)
    if body == 0:
        return None
    us = _upper_shadow(c)
    ls = _lower_shadow(c)
    r = _range(c)
    if r == 0:
        return None
    # Upper shadow at least 2x body, lower shadow less than 10% of range
    if us > 2.0 * body and ls < 0.1 * r:
        return {"pattern": "shooting_star", "confidence": 0.75, "type": "bearish"}
    return None


def marubozu(candles: list[Candle]) -> dict[str, Any] | None:
    """Marubozu: body fills nearly entire range (shadows < 5%)."""
    if not candles:
        return None
    c = candles[-1]
    r = _range(c)
    if r == 0:
        return None
    if _body(c) / r > 0.95:
        return {
            "pattern": "marubozu_bull" if _is_bullish(c) else "marubozu_bear",
            "confidence": 0.7,
            "type": "bullish" if _is_bullish(c) else "bearish",
        }
    return None


# ────────────────────────── Two-candle patterns ──────────────────────────

def engulfing(candles: list[Candle]) -> dict[str, Any] | None:
    """Bullish/bearish engulfing."""
    if len(candles) < 2:
        return None
    prev, curr = candles[-2], candles[-1]
    prev_body = _body(prev)
    curr_body = _body(curr)
    if prev_body == 0 or curr_body == 0:
        return None
    # Bullish engulfing: prev bearish, curr bullish, curr body engulfs prev body
    if _is_bearish(prev) and _is_bullish(curr):
        if float(curr.close) >= float(prev.open) and float(curr.open) <= float(prev.close):
            return {"pattern": "bullish_engulfing", "confidence": 0.85, "type": "bullish"}
    # Bearish engulfing: prev bullish, curr bearish, curr body engulfs prev body
    if _is_bullish(prev) and _is_bearish(curr):
        if float(curr.open) >= float(prev.close) and float(curr.close) <= float(prev.open):
            return {"pattern": "bearish_engulfing", "confidence": 0.85, "type": "bearish"}
    return None


def harami(candles: list[Candle]) -> dict[str, Any] | None:
    """Bullish/bearish harami (inside bar)."""
    if len(candles) < 2:
        return None
    prev, curr = candles[-2], candles[-1]
    # Current candle's range is inside the previous candle's range
    if float(curr.high) <= float(prev.high) and float(curr.low) >= float(prev.low):
        if _is_bearish(prev) and _is_bullish(curr):
            return {"pattern": "bullish_harami", "confidence": 0.7, "type": "bullish"}
        if _is_bullish(prev) and _is_bearish(curr):
            return {"pattern": "bearish_harami", "confidence": 0.7, "type": "bearish"}
    return None


def piercing_line(candles: list[Candle]) -> dict[str, Any] | None:
    """Piercing line: bearish candle followed by bullish that closes above midpoint."""
    if len(candles) < 2:
        return None
    prev, curr = candles[-2], candles[-1]
    if not _is_bearish(prev) or not _is_bullish(curr):
        return None
    midpoint = (float(prev.open) + float(prev.close)) / 2.0
    if float(curr.close) > midpoint and float(curr.open) < float(prev.close):
        return {"pattern": "piercing_line", "confidence": 0.75, "type": "bullish"}
    return None


def dark_cloud_cover(candles: list[Candle]) -> dict[str, Any] | None:
    """Dark cloud cover: bullish then bearish closing below midpoint."""
    if len(candles) < 2:
        return None
    prev, curr = candles[-2], candles[-1]
    if not _is_bullish(prev) or not _is_bearish(curr):
        return None
    midpoint = (float(prev.open) + float(prev.close)) / 2.0
    if float(curr.close) < midpoint and float(curr.open) > float(prev.close):
        return {"pattern": "dark_cloud_cover", "confidence": 0.75, "type": "bearish"}
    return None


# ────────────────────────── Three-candle patterns ──────────────────────────

def morning_star(candles: list[Candle]) -> dict[str, Any] | None:
    """Morning star: bearish → small body → bullish closing above first midpoint."""
    if len(candles) < 3:
        return None
    c1, c2, c3 = candles[-3], candles[-2], candles[-1]
    if not _is_bearish(c1):
        return None
    if _body(c2) > _body(c1) * 0.5:
        return None
    if not _is_bullish(c3):
        return None
    mid1 = (float(c1.open) + float(c1.close)) / 2.0
    if float(c3.close) > mid1:
        return {"pattern": "morning_star", "confidence": 0.85, "type": "bullish"}
    return None


def evening_star(candles: list[Candle]) -> dict[str, Any] | None:
    """Evening star: bullish → small body → bearish closing below first midpoint."""
    if len(candles) < 3:
        return None
    c1, c2, c3 = candles[-3], candles[-2], candles[-1]
    if not _is_bullish(c1):
        return None
    if _body(c2) > _body(c1) * 0.5:
        return None
    if not _is_bearish(c3):
        return None
    mid1 = (float(c1.open) + float(c1.close)) / 2.0
    if float(c3.close) < mid1:
        return {"pattern": "evening_star", "confidence": 0.85, "type": "bearish"}
    return None


def three_white_soldiers(candles: list[Candle]) -> dict[str, Any] | None:
    """Three white soldiers: three consecutive bullish candles, each closing higher."""
    if len(candles) < 3:
        return None
    c1, c2, c3 = candles[-3], candles[-2], candles[-1]
    if not all(_is_bullish(c) for c in (c1, c2, c3)):
        return None
    if float(c2.close) > float(c1.close) and float(c3.close) > float(c2.close):
        if float(c2.open) > float(c1.open) and float(c3.open) > float(c2.open):
            return {"pattern": "three_white_soldiers", "confidence": 0.9, "type": "bullish"}
    return None


def three_black_crows(candles: list[Candle]) -> dict[str, Any] | None:
    """Three black crows: three consecutive bearish candles, each closing lower."""
    if len(candles) < 3:
        return None
    c1, c2, c3 = candles[-3], candles[-2], candles[-1]
    if not all(_is_bearish(c) for c in (c1, c2, c3)):
        return None
    if float(c2.close) < float(c1.close) and float(c3.close) < float(c2.close):
        if float(c2.open) < float(c1.open) and float(c3.open) < float(c2.open):
            return {"pattern": "three_black_crows", "confidence": 0.9, "type": "bearish"}
    return None


# ────────────────────────── Chart patterns ──────────────────────────

def double_bottom(candles: list[Candle], lookback: int = 20) -> dict[str, Any] | None:
    """Double bottom: two lows at similar price with a peak between them."""
    if len(candles) < lookback:
        return None
    window = candles[-lookback:]
    lows = [float(c.low) for c in window]
    if len(lows) < 5:
        return None
    # Find two lowest points
    sorted_idx = sorted(range(len(lows)), key=lambda i: lows[i])[:2]
    sorted_idx.sort()
    i1, i2 = sorted_idx
    if i2 - i1 < 3:
        return None
    # Trough similarity
    if abs(lows[i1] - lows[i2]) / max(lows[i1], lows[i2], 1e-9) > 0.02:
        return None
    # Peak between them
    between = lows[i1 + 1 : i2]
    if not between or max(between) <= lows[i1] * 1.01:
        return None
    return {"pattern": "double_bottom", "confidence": 0.7, "type": "bullish"}


def double_top(candles: list[Candle], lookback: int = 20) -> dict[str, Any] | None:
    """Double top: two highs at similar price with a trough between them."""
    if len(candles) < lookback:
        return None
    window = candles[-lookback:]
    highs = [float(c.high) for c in window]
    if len(highs) < 5:
        return None
    sorted_idx = sorted(range(len(highs)), key=lambda i: -highs[i])[:2]
    sorted_idx.sort()
    i1, i2 = sorted_idx
    if i2 - i1 < 3:
        return None
    if abs(highs[i1] - highs[i2]) / max(highs[i1], highs[i2], 1e-9) > 0.02:
        return None
    between = highs[i1 + 1 : i2]
    if not between or min(between) >= highs[i1] * 0.99:
        return None
    return {"pattern": "double_top", "confidence": 0.7, "type": "bearish"}


def breakout(candles: list[Candle], lookback: int = 20) -> dict[str, Any] | None:
    """Breakout: close exceeds the highest high of the prior lookback window."""
    if len(candles) < lookback + 1:
        return None
    prior = candles[-(lookback + 1) : -1]
    curr = candles[-1]
    hh = max(float(c.high) for c in prior)
    ll = min(float(c.low) for c in prior)
    close = float(curr.close)
    if close > hh:
        return {"pattern": "breakout_bullish", "confidence": 0.8, "type": "bullish", "level": hh}
    if close < ll:
        return {"pattern": "breakout_bearish", "confidence": 0.8, "type": "bearish", "level": ll}
    return None


# ────────────────────────── Aggregate ──────────────────────────

_PATTERN_FUNCS = [
    doji, hammer, shooting_star, marubozu,
    engulfing, harami, piercing_line, dark_cloud_cover,
    morning_star, evening_star, three_white_soldiers, three_black_crows,
    double_bottom, double_top, breakout,
]


def detect_patterns(candles: list[Candle]) -> list[dict[str, Any]]:
    """Run all pattern detectors and return a list of detected patterns."""
    found: list[dict[str, Any]] = []
    for func in _PATTERN_FUNCS:
        result = func(candles)
        if result:
            found.append(result)
    return found
