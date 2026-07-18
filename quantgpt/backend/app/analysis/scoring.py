"""Normalized scoring engine.

Combines indicator signals, pattern signals, and optional fundamental/
sentiment/sector inputs into a single 0-100 score per stock. The score
represents overall bullish intelligence strength — higher = more bullish.

Scoring is a weighted sum of sub-scores, each normalized to 0-100:
  - Technical score (trend, momentum, volatility position)
  - Pattern score (bullish/bearish candlestick & chart patterns)
  - Volume score (volume trend and confirmation)
  - Fundamental score (optional, from fundamental agent)
  - Sentiment score (optional, from sentiment agent)
  - Sector score (optional, from sector strength agent)
  - Relative strength score (optional, vs benchmark)

Weights are configurable; defaults favor technicals since that's what
we can compute from price data alone.
"""

from __future__ import annotations

from typing import Any

from app.analysis import indicators as ind
from app.analysis import patterns as pat


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _rescale(value: float, in_lo: float, in_hi: float, out_lo: float = 0.0, out_hi: float = 100.0) -> float:
    """Linear rescale from [in_lo, in_hi] to [out_lo, out_hi]."""
    if in_hi == in_lo:
        return (out_lo + out_hi) / 2.0
    return out_lo + (value - in_lo) * (out_hi - out_lo) / (in_hi - in_lo)


# ────────────────────────── Sub-scores ──────────────────────────

def technical_score(indics: dict[str, Any]) -> float:
    """Score from technical indicators (0-100)."""
    score = 50.0  # neutral start

    # EMA trend: EMA9 vs EMA21 vs EMA50
    ema9 = indics.get("flat", {}).get("ema_9")
    ema21 = indics.get("flat", {}).get("ema_21")
    ema50 = indics.get("flat", {}).get("ema_50")
    ema200 = indics.get("flat", {}).get("ema_200")
    if ema9 and ema21:
        if ema9 > ema21:
            score += 5
        else:
            score -= 5
    if ema21 and ema50:
        if ema21 > ema50:
            score += 5
        else:
            score -= 5
    if ema50 and ema200:
        if ema50 > ema200:
            score += 5  # long-term uptrend
        else:
            score -= 5

    # MACD: positive histogram = bullish
    macd_hist = indics.get("flat", {}).get("macd_histogram")
    macd_line = indics.get("flat", {}).get("macd_macd")
    macd_signal = indics.get("flat", {}).get("macd_signal")
    if macd_hist is not None:
        score += _rescale(macd_hist, -2, 2, -10, 10)
    if macd_line is not None and macd_signal is not None:
        if macd_line > macd_signal:
            score += 3

    # RSI: 50-70 is bullish momentum, >70 overbought, <30 oversold
    rsi = indics.get("flat", {}).get("rsi_14")
    if rsi is not None:
        if 50 <= rsi <= 70:
            score += 8
        elif 30 <= rsi < 50:
            score -= 3
        elif rsi > 70:
            score -= 5  # overbought
        elif rsi < 30:
            score += 3  # oversold bounce potential

    # ADX: trend strength
    adx_val = indics.get("flat", {}).get("adx_adx")
    plus_di = indics.get("flat", {}).get("adx_plus_di")
    minus_di = indics.get("flat", {}).get("adx_minus_di")
    if adx_val is not None:
        if adx_val > 25:
            score += 5  # strong trend
            if plus_di is not None and minus_di is not None:
                if plus_di > minus_di:
                    score += 3
                else:
                    score -= 3

    # Supertrend
    st_trend = indics.get("flat", {}).get("supertrend_trend")
    if st_trend == "up":
        score += 5
    elif st_trend == "down":
        score -= 5

    # Ichimoku: price above cloud (senkou_a > senkou_b = bullish cloud)
    tenkan = indics.get("flat", {}).get("ichimoku_tenkan")
    kijun = indics.get("flat", {}).get("ichimoku_kijun")
    if tenkan and kijun:
        if tenkan > kijun:
            score += 4
        else:
            score -= 4

    # Bollinger %B: near lower band = potential oversold
    bb_pct = indics.get("flat", {}).get("bollinger_percent")
    if bb_pct is not None:
        if bb_pct < 0.2:
            score += 3  # near lower band
        elif bb_pct > 0.8:
            score -= 3  # near upper band

    # Stochastic
    stoch_k = indics.get("flat", {}).get("stochastic_k")
    if stoch_k is not None:
        if 20 <= stoch_k <= 80:
            if stoch_k > 50:
                score += 2
        elif stoch_k < 20:
            score += 3  # oversold
        elif stoch_k > 80:
            score -= 3  # overbought

    # Aroon
    aroon_up = indics.get("flat", {}).get("aroon_up")
    aroon_down = indics.get("flat", {}).get("aroon_down")
    if aroon_up is not None and aroon_down is not None:
        if aroon_up > aroon_down:
            score += 3
        else:
            score -= 3

    return _clamp(score)


def pattern_score(detected: list[dict[str, Any]]) -> float:
    """Score from detected patterns (0-100). 50 = neutral."""
    score = 50.0
    for p in detected:
        conf = p.get("confidence", 0.5)
        ptype = p.get("type", "neutral")
        if ptype == "bullish":
            score += 8 * conf
        elif ptype == "bearish":
            score -= 8 * conf
    return _clamp(score)


def volume_score(candles: list[dict[str, Any]]) -> float:
    """Score from volume analysis (0-100). 50 = neutral."""
    if len(candles) < 20:
        return 50.0
    vols = [c.get("volume") or 0 for c in candles[-20:]]
    recent = sum(vols[-5:]) / 5 if len(vols) >= 5 else vols[-1]
    avg = sum(vols) / len(vols) if vols else 0
    if avg == 0:
        return 50.0
    ratio = recent / avg
    # Higher volume on recent candles = confirmation
    if ratio > 1.5:
        return 70.0
    elif ratio > 1.2:
        return 60.0
    elif ratio < 0.7:
        return 40.0
    elif ratio < 0.5:
        return 30.0
    return 50.0


def relative_strength_score(symbol_return: float, benchmark_return: float) -> float:
    """Score relative strength vs benchmark (0-100)."""
    diff = symbol_return - benchmark_return
    return _clamp(50.0 + _rescale(diff, -10, 10, -40, 40))


# ────────────────────────── Main score ──────────────────────────

DEFAULT_WEIGHTS: dict[str, float] = {
    "technical": 0.35,
    "pattern": 0.15,
    "volume": 0.10,
    "fundamental": 0.15,
    "sentiment": 0.10,
    "sector": 0.10,
    "relative_strength": 0.05,
}


def compute_score(
    *,
    indics: dict[str, Any] | None = None,
    detected_patterns: list[dict[str, Any]] | None = None,
    candles_raw: list[dict[str, Any]] | None = None,
    fundamental: float | None = None,
    sentiment: float | None = None,
    sector: float | None = None,
    relative_strength: float | None = None,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compute a normalized 0-100 intelligence score for a stock.

    Returns the composite score plus all sub-scores and the weights used.
    Missing inputs default to 50 (neutral) so the score is always valid.
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    tech = technical_score(indics or {})
    pat_s = pattern_score(detected_patterns or [])
    vol = volume_score(candles_raw or [])
    fund = fundamental if fundamental is not None else 50.0
    sent = sentiment if sentiment is not None else 50.0
    sec = sector if sector is not None else 50.0
    rs = relative_strength if relative_strength is not None else 50.0

    composite = (
        w["technical"] * tech
        + w["pattern"] * pat_s
        + w["volume"] * vol
        + w["fundamental"] * fund
        + w["sentiment"] * sent
        + w["sector"] * sec
        + w["relative_strength"] * rs
    )
    composite = _clamp(composite)

    return {
        "score": round(composite, 2),
        "sub_scores": {
            "technical": round(tech, 2),
            "pattern": round(pat_s, 2),
            "volume": round(vol, 2),
            "fundamental": round(fund, 2),
            "sentiment": round(sent, 2),
            "sector": round(sec, 2),
            "relative_strength": round(rs, 2),
        },
        "weights": w,
        "signal": _signal_from_score(composite),
    }


def _signal_from_score(score: float) -> str:
    if score >= 75:
        return "strong_bullish"
    if score >= 60:
        return "bullish"
    if score >= 40:
        return "neutral"
    if score >= 25:
        return "bearish"
    return "strong_bearish"
