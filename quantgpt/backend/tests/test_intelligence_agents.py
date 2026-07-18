"""Tests for the intelligence agents."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

from app.agents.intelligence import (
    FundamentalAnalysisAgent,
    IndicatorEngineAgent,
    MarketScannerAgent,
    MomentumAgent,
    NewsAgent,
    PatternRecognitionAgent,
    RelativeStrengthAgent,
    SectorStrengthAgent,
    SentimentAgent,
    TechnicalAnalysisAgent,
    VolumeAnalysisAgent,
)
from app.integration.models import Candle


def _candles(prices: list[float], volumes: list[int] | None = None) -> list[Candle]:
    out: list[Candle] = []
    for i, p in enumerate(prices):
        o = prices[i - 1] if i > 0 else p
        h = max(o, p) * 1.005
        l = min(o, p) * 0.995
        v = volumes[i] if volumes and i < len(volumes) else 1000
        out.append(Candle(
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open=Decimal(str(o)), high=Decimal(str(h)),
            low=Decimal(str(l)), close=Decimal(str(p)), volume=v,
        ))
    return out


def _mock_facade(prices: list[float], volumes: list[int] | None = None) -> MagicMock:
    facade = MagicMock()
    facade.history.return_value = _candles(prices, volumes)
    return facade


def _build_agent(cls, facade=None):
    return cls(
        agent_id="00000000-0000-0000-0000-000000000000",
        db=MagicMock(),
        config={},
        facade=facade,
    )


class TestTechnicalAnalysisAgent:
    def test_with_candles(self):
        prices = [100 + i * 0.5 for i in range(60)]
        facade = _mock_facade(prices)
        agent = _build_agent(TechnicalAnalysisAgent, facade=facade)
        result = agent.execute({"symbol": "TEST", "exchange": "NSE"})
        assert "score" in result
        assert result["score"] > 0
        assert "indicators" in result
        assert result["candle_count"] == 60

    def test_insufficient_data(self):
        facade = _mock_facade([100, 101, 102])
        agent = _build_agent(TechnicalAnalysisAgent, facade=facade)
        result = agent.execute({"symbol": "TEST"})
        assert "error" in result

    def test_no_facade(self):
        agent = _build_agent(TechnicalAnalysisAgent)
        result = agent.execute({"symbol": "TEST"})
        assert "error" in result


class TestFundamentalAnalysisAgent:
    def test_with_candles(self):
        prices = [100 + i * 0.3 for i in range(60)]
        facade = _mock_facade(prices)
        agent = _build_agent(FundamentalAnalysisAgent, facade=facade)
        result = agent.execute({"symbol": "TEST"})
        assert "score" in result
        assert "return_200d" in result
        assert "volatility_annual" in result

    def test_insufficient_data(self):
        facade = _mock_facade([100, 101])
        agent = _build_agent(FundamentalAnalysisAgent, facade=facade)
        result = agent.execute({"symbol": "TEST"})
        assert "error" in result


class TestNewsAgent:
    def test_returns_neutral(self):
        agent = _build_agent(NewsAgent)
        result = agent.execute({"symbol": "TEST"})
        assert result["score"] == 50
        assert result["headlines"] == []


class TestSentimentAgent:
    def test_bullish_sentiment(self):
        prices = [100 + i for i in range(30)]
        facade = _mock_facade(prices)
        agent = _build_agent(SentimentAgent, facade=facade)
        result = agent.execute({"symbol": "TEST"})
        assert result["score"] > 50
        assert result["label"] == "bullish"

    def test_bearish_sentiment(self):
        prices = [100 - i for i in range(30)]
        facade = _mock_facade(prices)
        agent = _build_agent(SentimentAgent, facade=facade)
        result = agent.execute({"symbol": "TEST"})
        assert result["score"] < 50
        assert result["label"] == "bearish"


class TestSectorStrengthAgent:
    def test_no_sector(self):
        agent = _build_agent(SectorStrengthAgent)
        result = agent.execute({})
        assert "error" in result

    def test_with_sector_data(self):
        prices = [100 + i for i in range(30)]
        facade = _mock_facade(prices)
        agent = _build_agent(SectorStrengthAgent, facade=facade)
        result = agent.execute({"sector": "NIFTY IT"})
        assert "score" in result
        assert result["strength"] in ("strong", "weak", "neutral")


class TestRelativeStrengthAgent:
    def test_outperformance(self):
        sym_prices = [100 + i * 2 for i in range(30)]
        bench_prices = [100 + i * 0.5 for i in range(30)]
        facade = MagicMock()
        facade.history.side_effect = [_candles(sym_prices), _candles(bench_prices)]
        agent = _build_agent(RelativeStrengthAgent, facade=facade)
        result = agent.execute({"symbol": "TEST", "benchmark": "NIFTY 50"})
        assert result["score"] > 50
        assert result["outperformance"] > 0

    def test_no_symbol(self):
        agent = _build_agent(RelativeStrengthAgent)
        result = agent.execute({})
        assert "error" in result


class TestMomentumAgent:
    def test_strong_momentum(self):
        prices = [100 + i for i in range(30)]
        facade = _mock_facade(prices)
        agent = _build_agent(MomentumAgent, facade=facade)
        result = agent.execute({"symbol": "TEST"})
        assert result["score"] > 60
        assert "roc_5" in result
        assert "roc_20" in result

    def test_insufficient_data(self):
        facade = _mock_facade([100, 101])
        agent = _build_agent(MomentumAgent, facade=facade)
        result = agent.execute({"symbol": "TEST"})
        assert "error" in result


class TestVolumeAnalysisAgent:
    def test_volume_analysis(self):
        prices = [100 + i * 0.5 for i in range(30)]
        volumes = [1000] * 20 + [2000] * 10
        facade = _mock_facade(prices, volumes)
        agent = _build_agent(VolumeAnalysisAgent, facade=facade)
        result = agent.execute({"symbol": "TEST"})
        assert "score" in result
        assert "obv" in result
        assert "price_volume_confirmation" in result


class TestIndicatorEngineAgent:
    def test_all_indicators_present(self):
        prices = [100 + i * 0.5 for i in range(60)]
        facade = _mock_facade(prices)
        agent = _build_agent(IndicatorEngineAgent, facade=facade)
        result = agent.execute({"symbol": "TEST"})
        assert "indicators" in result
        assert "ema" in result["indicators"]
        assert "macd" in result["indicators"]
        assert "rsi" in result["indicators"]
        assert "adx" in result["indicators"]
        assert "atr" in result["indicators"]
        assert "vwap" in result["indicators"]
        assert "supertrend" in result["indicators"]
        assert "ichimoku" in result["indicators"]
        assert "bollinger" in result["indicators"]
        assert "donchian" in result["indicators"]


class TestPatternRecognitionAgent:
    def test_pattern_detection(self):
        # Build candles with a bullish engulfing at the end
        prices = [100 + i * 0.5 for i in range(25)]
        candles = _candles(prices)
        # Add a bearish then bullish engulfing
        candles.append(_candles([100, 101])[0])
        candles.append(Candle(
            timestamp=datetime(2024, 2, 1, tzinfo=timezone.utc),
            open=Decimal("99"), high=Decimal("107"), low=Decimal("98"),
            close=Decimal("106"), volume=2000,
        ))
        facade = MagicMock()
        facade.history.return_value = candles
        agent = _build_agent(PatternRecognitionAgent, facade=facade)
        result = agent.execute({"symbol": "TEST"})
        assert "patterns" in result
        assert "pattern_count" in result
        assert "bullish_count" in result
        assert "bearish_count" in result


class TestMarketScannerAgent:
    def test_scan_multiple_symbols(self):
        prices = [100 + i * 0.5 for i in range(60)]
        facade = _mock_facade(prices)
        agent = _build_agent(MarketScannerAgent, facade=facade)
        result = agent.execute({"symbols": ["TEST1", "TEST2"], "exchange": "NSE"})
        assert "scans" in result
        assert result["count"] == 2
        assert "composite_score" in result["scans"][0]
        assert "signal" in result["scans"][0]

    def test_no_symbols(self):
        agent = _build_agent(MarketScannerAgent)
        result = agent.execute({})
        assert "error" in result

    def test_single_symbol_string(self):
        prices = [100 + i * 0.5 for i in range(60)]
        facade = _mock_facade(prices)
        agent = _build_agent(MarketScannerAgent, facade=facade)
        result = agent.execute({"symbols": "TEST", "exchange": "NSE"})
        assert result["count"] == 1

    def test_results_sorted_by_score(self):
        # First symbol has bullish data, second has bearish
        up_prices = [100 + i for i in range(60)]
        down_prices = [100 - i * 0.5 for i in range(60)]
        facade = MagicMock()
        facade.history.side_effect = [
            _candles(up_prices), _candles(down_prices),
            _candles(up_prices), _candles(down_prices),
            _candles(up_prices), _candles(down_prices),
            _candles(up_prices), _candles(down_prices),
            _candles(up_prices), _candles(down_prices),
        ]
        agent = _build_agent(MarketScannerAgent, facade=facade)
        result = agent.execute({"symbols": ["UP", "DOWN"], "exchange": "NSE"})
        assert result["scans"][0]["composite_score"] >= result["scans"][1]["composite_score"]
