"""Intelligence agents — real implementations for market analysis.

These 11 agents replace the placeholder stubs with working intelligence:
  Market Scanner, Technical Analysis, Fundamental Analysis, News,
  Sentiment, Sector Strength, Relative Strength, Momentum,
  Volume Analysis, Indicator Engine, Pattern Recognition.

All agents produce intelligence only — no trading, no order placement.
Each returns a normalized score (0-100) plus detailed analysis.
"""

from __future__ import annotations

import math
from typing import Any

from app.agents.base import AgentBase
from app.analysis import indicators as ind
from app.analysis import patterns as pat
from app.analysis import scoring


class _IntelligenceAgent(AgentBase):
    """Base for intelligence agents. Provides candle-fetching helper."""

    def _get_candles(self, payload: dict[str, Any], *, limit: int = 200) -> list[Any]:
        if not self._facade:
            return []
        symbol = payload.get("symbol", "")
        exchange = payload.get("exchange", "NSE")
        interval = payload.get("interval", "1d")
        try:
            return self._facade.history(symbol, exchange, interval, limit=limit)
        except Exception as e:
            self._log.warning("agent.candles_failed", agent=self.name, error=str(e))
            return []

    @staticmethod
    def _candles_to_dicts(candles: list[Any]) -> list[dict[str, Any]]:
        return [
            {
                "timestamp": str(c.timestamp),
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "volume": float(c.volume) if c.volume else 0.0,
            }
            for c in candles
        ]


class MarketScannerAgent(_IntelligenceAgent):
    """Scans the market for opportunities. Orchestrates a full scan across
    all intelligence dimensions for a symbol or list of symbols."""

    name = "market_scanner"
    type = "scanner"

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        symbols = payload.get("symbols", [])
        if isinstance(symbols, str):
            symbols = [symbols]
        if not symbols:
            return {"error": "no symbols provided", "scans": []}

        results = []
        for sym in symbols:
            sym_payload = {**payload, "symbol": sym}
            scan: dict[str, Any] = {"symbol": sym}

            # Technical
            tech = self._run_sub("technical_analysis", sym_payload)
            scan["technical"] = tech

            # Momentum
            mom = self._run_sub("momentum", sym_payload)
            scan["momentum"] = mom

            # Volume
            vol = self._run_sub("volume_analysis", sym_payload)
            scan["volume"] = vol

            # Patterns
            pats = self._run_sub("pattern_recognition", sym_payload)
            scan["patterns"] = pats

            # Indicator engine
            ie = self._run_sub("indicator_engine", sym_payload)
            scan["indicators"] = ie

            # Composite score
            tech_score = tech.get("score", 50) if isinstance(tech, dict) else 50
            mom_score = mom.get("score", 50) if isinstance(mom, dict) else 50
            vol_score = vol.get("score", 50) if isinstance(vol, dict) else 50
            pat_score = pats.get("score", 50) if isinstance(pats, dict) else 50

            composite = scoring.compute_score(
                fundamental=tech_score,
                sentiment=pat_score,
                sector=vol_score,
                weights={"technical": 0.0, "pattern": 0.0, "volume": 0.0,
                         "fundamental": 0.4, "sentiment": 0.2, "sector": 0.15,
                         "relative_strength": 0.25},
            )
            scan["composite_score"] = composite["score"]
            scan["signal"] = composite["signal"]
            results.append(scan)

        # Sort by composite score descending
        results.sort(key=lambda r: r.get("composite_score", 0), reverse=True)
        return {"scans": results, "count": len(results)}


    def _run_sub(self, agent_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Run a sub-analysis inline (computes directly without the manager)."""
        agent_map = {
            "technical_analysis": TechnicalAnalysisAgent,
            "momentum": MomentumAgent,
            "volume_analysis": VolumeAnalysisAgent,
            "pattern_recognition": PatternRecognitionAgent,
            "indicator_engine": IndicatorEngineAgent,
        }
        cls = agent_map.get(agent_name)
        if not cls:
            return {"error": f"unknown sub-agent {agent_name}"}
        sub = cls(agent_id=self.id, db=self._db, config=self._config, facade=self._facade)
        return sub.execute(payload)


class TechnicalAnalysisAgent(_IntelligenceAgent):
    """Computes all technical indicators and a technical score."""

    name = "technical_analysis"
    type = "analysis"

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        candles = self._get_candles(payload, limit=200)
        if len(candles) < 30:
            return {"error": "insufficient candle data", "candles": len(candles), "score": 50}

        indics = ind.all_indicators(candles)
        score = scoring.technical_score(indics)
        return {
            "symbol": payload.get("symbol"),
            "score": round(score, 2),
            "indicators": indics.get("flat", {}),
            "candle_count": len(candles),
        }


class FundamentalAnalysisAgent(_IntelligenceAgent):
    """Fundamental analysis. Without a fundamental data feed, this agent
    uses price-derived proxies (long-term trend, volatility-adjusted
    return) and returns a neutral-leaning score. Can be extended with a
    real fundamentals adapter later."""

    name = "fundamental_analysis"
    type = "analysis"

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        candles = self._get_candles(payload, limit=200)
        if len(candles) < 50:
            return {"error": "insufficient data", "score": 50}

        closes = [float(c.close) for c in candles]
        # Long-term return (200-period)
        ret_200 = (closes[-1] / closes[0] - 1) * 100 if closes[0] else 0
        # Volatility (annualized std of daily returns)
        rets = [(closes[i] / closes[i-1] - 1) for i in range(1, len(closes)) if closes[i-1]]
        vol = (math.sqrt(sum(r*r for r in rets) / len(rets)) * math.sqrt(252) * 100) if rets else 0
        # Sharpe-like ratio
        sharpe = (ret_200 / vol) if vol > 0 else 0

        # Score: map sharpe to 0-100
        score = scoring._clamp(50 + sharpe * 10)

        return {
            "symbol": payload.get("symbol"),
            "score": round(score, 2),
            "return_200d": round(ret_200, 2),
            "volatility_annual": round(vol, 2),
            "sharpe_proxy": round(sharpe, 2),
            "note": "proxy fundamentals from price data — connect a fundamentals feed for real metrics",
        }


class NewsAgent(_IntelligenceAgent):
    """News intelligence. Without a news feed, returns a neutral score.
    Designed to be connected to a news API adapter later."""

    name = "news"
    type = "information"

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "symbol": payload.get("symbol"),
            "score": 50,
            "headlines": [],
            "note": "no news feed configured — connect a news API to enable news intelligence",
        }


class SentimentAgent(_IntelligenceAgent):
    """Sentiment analysis. Without a sentiment feed, uses RSI and
    Bollinger Band position as price-based sentiment proxies."""

    name = "sentiment"
    type = "sentiment"

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        candles = self._get_candles(payload, limit=100)
        if len(candles) < 30:
            return {"error": "insufficient data", "score": 50}

        rsi = ind.rsi(candles, 14)
        bb = ind.bollinger_bands(candles)

        # RSI: >50 = bullish sentiment, <50 = bearish
        rsi_score = rsi if rsi is not None else 50
        # BB %B: near upper = euphoric, near lower = fearful
        bb_pct = bb.get("percent")
        if bb_pct is not None:
            bb_score = bb_pct * 100
        else:
            bb_score = 50

        # Blend: RSI is momentum sentiment, BB is position sentiment
        score = scoring._clamp(0.6 * rsi_score + 0.4 * bb_score)

        label = "bullish" if score > 60 else "bearish" if score < 40 else "neutral"

        return {
            "symbol": payload.get("symbol"),
            "score": round(score, 2),
            "label": label,
            "rsi_sentiment": round(rsi_score, 2),
            "bb_position_sentiment": round(bb_score, 2),
        }


class SectorStrengthAgent(_IntelligenceAgent):
    """Sector strength analysis. Without a sector index feed, returns
    neutral. Designed to compare sector indices when configured."""

    name = "sector_strength"
    type = "sector"

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        sector = payload.get("sector")
        if not sector:
            return {"error": "no sector specified", "score": 50}

        # If we have a facade, try to fetch sector index candles
        candles = self._get_candles({**payload, "symbol": sector}, limit=100)
        if len(candles) < 20:
            return {
                "sector": sector,
                "score": 50,
                "note": "insufficient sector data — using neutral default",
            }

        closes = [float(c.close) for c in candles]
        ret = (closes[-1] / closes[0] - 1) * 100 if closes[0] else 0
        score = scoring._clamp(50 + ret * 2)

        return {
            "sector": sector,
            "score": round(score, 2),
            "return_period": round(ret, 2),
            "strength": "strong" if score > 65 else "weak" if score < 35 else "neutral",
        }


class RelativeStrengthAgent(_IntelligenceAgent):
    """Relative strength vs a benchmark (e.g., NIFTY)."""

    name = "relative_strength"
    type = "relative_strength"

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        symbol = payload.get("symbol")
        benchmark = payload.get("benchmark", "NIFTY 50")
        if not symbol:
            return {"error": "no symbol provided", "score": 50}

        sym_candles = self._get_candles({**payload, "symbol": symbol}, limit=100)
        bench_candles = self._get_candles({**payload, "symbol": benchmark}, limit=100)

        if len(sym_candles) < 20 or len(bench_candles) < 20:
            return {"error": "insufficient data", "score": 50}

        sym_ret = (float(sym_candles[-1].close) / float(sym_candles[0].close) - 1) * 100
        bench_ret = (float(bench_candles[-1].close) / float(bench_candles[0].close) - 1) * 100
        rs_score = scoring.relative_strength_score(sym_ret, bench_ret)

        return {
            "symbol": symbol,
            "benchmark": benchmark,
            "score": round(rs_score, 2),
            "symbol_return": round(sym_ret, 2),
            "benchmark_return": round(bench_ret, 2),
            "outperformance": round(sym_ret - bench_ret, 2),
        }


class MomentumAgent(_IntelligenceAgent):
    """Momentum analysis using rate of change, RSI, MACD, and ADX."""

    name = "momentum"
    type = "momentum"

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        candles = self._get_candles(payload, limit=100)
        if len(candles) < 30:
            return {"error": "insufficient data", "score": 50}

        closes = [float(c.close) for c in candles]
        # Rate of change (various periods)
        roc_5 = ((closes[-1] / closes[-6] - 1) * 100) if len(closes) >= 6 else 0
        roc_20 = ((closes[-1] / closes[-21] - 1) * 100) if len(closes) >= 21 else 0
        rsi_val = ind.rsi(candles, 14)
        macd_data = ind.macd(candles)
        adx_data = ind.adx(candles)

        score = 50.0
        # ROC contribution
        score += scoring._rescale(roc_5, -10, 10, -15, 15)
        score += scoring._rescale(roc_20, -20, 20, -10, 10)
        # RSI momentum
        if rsi_val is not None:
            if 50 <= rsi_val <= 70:
                score += 8
            elif rsi_val > 70:
                score -= 5
            elif rsi_val < 30:
                score += 3
        # MACD momentum
        hist = macd_data.get("histogram")
        if hist is not None:
            score += scoring._rescale(hist, -2, 2, -8, 8)
        # ADX strength
        adx_val = adx_data.get("adx")
        if adx_val is not None and adx_val > 25:
            score += 5

        score = scoring._clamp(score)

        return {
            "symbol": payload.get("symbol"),
            "score": round(score, 2),
            "roc_5": round(roc_5, 2),
            "roc_20": round(roc_20, 2),
            "rsi": round(rsi_val, 2) if rsi_val else None,
            "macd_histogram": round(hist, 4) if hist else None,
            "adx": round(adx_val, 2) if adx_val else None,
        }


class VolumeAnalysisAgent(_IntelligenceAgent):
    """Volume analysis: volume trend, volume-price confirmation, OBV."""

    name = "volume_analysis"
    type = "volume"

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        candles = self._get_candles(payload, limit=100)
        if len(candles) < 20:
            return {"error": "insufficient data", "score": 50}

        candle_dicts = self._candles_to_dicts(candles)
        vol_score = scoring.volume_score(candle_dicts)
        obv_val = ind.obv(candles)

        # Volume-price confirmation: rising price + rising volume = bullish
        closes = [float(c.close) for c in candles]
        vols = [float(c.volume) if c.volume else 0 for c in candles]
        price_up = closes[-1] > closes[-5] if len(closes) >= 5 else False
        vol_up = sum(vols[-5:]) / 5 > (sum(vols[-20:]) / 20) if len(vols) >= 20 else False

        confirmation = "bullish" if (price_up and vol_up) else "bearish" if (not price_up and vol_up) else "neutral"

        return {
            "symbol": payload.get("symbol"),
            "score": round(vol_score, 2),
            "obv": round(obv_val, 2) if obv_val else None,
            "price_volume_confirmation": confirmation,
            "avg_volume_20": round(sum(vols[-20:]) / 20, 2) if len(vols) >= 20 else None,
            "recent_volume_5": round(sum(vols[-5:]) / 5, 2) if len(vols) >= 5 else None,
        }


class IndicatorEngineAgent(_IntelligenceAgent):
    """Computes all 10 supported indicators and returns them in a
    structured, normalized format."""

    name = "indicator_engine"
    type = "indicator"

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        candles = self._get_candles(payload, limit=200)
        if len(candles) < 30:
            return {"error": "insufficient data", "indicators": {}, "score": 50}

        indics = ind.all_indicators(candles)
        flat = indics.get("flat", {})

        # Build structured indicator output
        result = {
            "symbol": payload.get("symbol"),
            "score": round(scoring.technical_score(indics), 2),
            "indicators": {
                "ema": {
                    "ema_9": flat.get("ema_9"),
                    "ema_21": flat.get("ema_21"),
                    "ema_50": flat.get("ema_50"),
                    "ema_200": flat.get("ema_200"),
                },
                "macd": {
                    "macd_line": flat.get("macd_macd"),
                    "signal_line": flat.get("macd_signal"),
                    "histogram": flat.get("macd_histogram"),
                },
                "rsi": flat.get("rsi_14"),
                "adx": {
                    "adx": flat.get("adx_adx"),
                    "plus_di": flat.get("adx_plus_di"),
                    "minus_di": flat.get("adx_minus_di"),
                },
                "atr": flat.get("atr_14"),
                "vwap": flat.get("vwap"),
                "supertrend": {
                    "trend": flat.get("supertrend_trend"),
                    "value": flat.get("supertrend_value"),
                    "upper": flat.get("supertrend_upper"),
                    "lower": flat.get("supertrend_lower"),
                },
                "ichimoku": {
                    "tenkan": flat.get("ichimoku_tenkan"),
                    "kijun": flat.get("ichimoku_kijun"),
                    "senkou_a": flat.get("ichimoku_senkou_a"),
                    "senkou_b": flat.get("ichimoku_senkou_b"),
                },
                "bollinger": {
                    "upper": flat.get("bollinger_upper"),
                    "middle": flat.get("bollinger_middle"),
                    "lower": flat.get("bollinger_lower"),
                    "width": flat.get("bollinger_width"),
                    "percent": flat.get("bollinger_percent"),
                },
                "donchian": {
                    "upper": flat.get("donchian_upper"),
                    "middle": flat.get("donchian_middle"),
                    "lower": flat.get("donchian_lower"),
                },
            },
            "candle_count": len(candles),
        }
        return result


class PatternRecognitionAgent(_IntelligenceAgent):
    """Detects candlestick and chart patterns."""

    name = "pattern_recognition"
    type = "pattern"

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        candles = self._get_candles(payload, limit=100)
        if len(candles) < 5:
            return {"error": "insufficient data", "patterns": [], "score": 50}

        detected = pat.detect_patterns(candles)
        score = scoring.pattern_score(detected)

        return {
            "symbol": payload.get("symbol"),
            "score": round(score, 2),
            "patterns": detected,
            "pattern_count": len(detected),
            "bullish_count": sum(1 for p in detected if p.get("type") == "bullish"),
            "bearish_count": sum(1 for p in detected if p.get("type") == "bearish"),
        }


# ────────────────────────── Registration ──────────────────────────

# Intelligence agents that replace placeholders
INTELLIGENCE_AGENT_CLASSES: list[type[_IntelligenceAgent]] = [
    MarketScannerAgent,
    TechnicalAnalysisAgent,
    FundamentalAnalysisAgent,
    NewsAgent,
    SentimentAgent,
    SectorStrengthAgent,
    RelativeStrengthAgent,
    MomentumAgent,
    VolumeAnalysisAgent,
    IndicatorEngineAgent,
    PatternRecognitionAgent,
]

# Map of agent name -> class for lookup
INTELLIGENCE_AGENT_MAP: dict[str, type[_IntelligenceAgent]] = {
    cls.name: cls for cls in INTELLIGENCE_AGENT_CLASSES
}
