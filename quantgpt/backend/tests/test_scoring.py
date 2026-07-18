"""Tests for the scoring engine."""

from __future__ import annotations

from app.analysis import scoring


class TestTechnicalScore:
    def test_neutral_when_no_data(self):
        score = scoring.technical_score({})
        assert 40 <= score <= 60

    def test_bullish_ema_stack(self):
        indics = {"flat": {"ema_9": 105, "ema_21": 103, "ema_50": 100, "ema_200": 95}}
        score = scoring.technical_score(indics)
        assert score > 60

    def test_bearish_ema_stack(self):
        indics = {"flat": {"ema_9": 95, "ema_21": 97, "ema_50": 100, "ema_200": 105}}
        score = scoring.technical_score(indics)
        assert score < 40

    def test_rsi_bullish_zone(self):
        indics = {"flat": {"rsi_14": 65}}
        score = scoring.technical_score(indics)
        assert score > 55

    def test_rsi_overbought(self):
        indics = {"flat": {"rsi_14": 80}}
        score = scoring.technical_score(indics)
        assert score < 55


class TestPatternScore:
    def test_no_patterns(self):
        score = scoring.pattern_score([])
        assert score == 50.0

    def test_bullish_patterns(self):
        patterns = [
            {"pattern": "hammer", "confidence": 0.8, "type": "bullish"},
            {"pattern": "morning_star", "confidence": 0.85, "type": "bullish"},
        ]
        score = scoring.pattern_score(patterns)
        assert score > 60

    def test_bearish_patterns(self):
        patterns = [
            {"pattern": "shooting_star", "confidence": 0.8, "type": "bearish"},
            {"pattern": "evening_star", "confidence": 0.85, "type": "bearish"},
        ]
        score = scoring.pattern_score(patterns)
        assert score < 40


class TestVolumeScore:
    def test_insufficient_data(self):
        assert scoring.volume_score([]) == 50.0

    def test_high_volume(self):
        candles = [{"volume": 1000} for _ in range(15)] + [{"volume": 2000} for _ in range(5)]
        score = scoring.volume_score(candles)
        assert score > 50

    def test_low_volume(self):
        candles = [{"volume": 2000} for _ in range(15)] + [{"volume": 500} for _ in range(5)]
        score = scoring.volume_score(candles)
        assert score < 50


class TestRelativeStrength:
    def test_outperformance(self):
        score = scoring.relative_strength_score(10, 2)
        assert score > 70

    def test_underperformance(self):
        score = scoring.relative_strength_score(-5, 5)
        assert score < 30


class TestComputeScore:
    def test_default_neutral(self):
        result = scoring.compute_score()
        assert 40 <= result["score"] <= 60
        assert result["signal"] == "neutral"
        assert "sub_scores" in result
        assert "weights" in result

    def test_all_bullish(self):
        result = scoring.compute_score(
            indics={"flat": {"ema_9": 105, "ema_21": 103, "ema_50": 100, "ema_200": 95, "rsi_14": 65}},
            detected_patterns=[{"pattern": "hammer", "confidence": 0.8, "type": "bullish"}],
            candles_raw=[{"volume": 1000}] * 15 + [{"volume": 2000}] * 5,
            fundamental=70,
            sentiment=70,
            sector=65,
            relative_strength=75,
        )
        assert result["score"] > 60
        assert result["signal"] in ("bullish", "strong_bullish")

    def test_all_bearish(self):
        result = scoring.compute_score(
            indics={"flat": {"ema_9": 95, "ema_21": 97, "ema_50": 100, "ema_200": 105, "rsi_14": 25}},
            detected_patterns=[{"pattern": "shooting_star", "confidence": 0.8, "type": "bearish"}],
            candles_raw=[{"volume": 2000}] * 15 + [{"volume": 500}] * 5,
            fundamental=30,
            sentiment=30,
            sector=35,
            relative_strength=25,
        )
        assert result["score"] < 40
        assert result["signal"] in ("bearish", "strong_bearish")

    def test_custom_weights(self):
        result = scoring.compute_score(
            fundamental=100,
            weights={"technical": 0, "pattern": 0, "volume": 0, "fundamental": 1.0,
                     "sentiment": 0, "sector": 0, "relative_strength": 0},
        )
        assert result["score"] == 100.0

    def test_signal_thresholds(self):
        assert scoring._signal_from_score(80) == "strong_bullish"
        assert scoring._signal_from_score(65) == "bullish"
        assert scoring._signal_from_score(50) == "neutral"
        assert scoring._signal_from_score(30) == "bearish"
        assert scoring._signal_from_score(15) == "strong_bearish"
