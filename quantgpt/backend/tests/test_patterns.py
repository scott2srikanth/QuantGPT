"""Tests for pattern recognition."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.analysis import patterns as pat
from app.integration.models import Candle


def _candle(o, h, l, c, v=1000):
    return Candle(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=Decimal(str(o)), high=Decimal(str(h)),
        low=Decimal(str(l)), close=Decimal(str(c)), volume=v,
    )


class TestDoji:
    def test_doji_detected(self):
        c = _candle(100, 102, 98, 100.1)
        result = pat.doji([c])
        assert result is not None
        assert result["pattern"] == "doji"
        assert result["type"] == "neutral"

    def test_no_doji(self):
        c = _candle(100, 105, 95, 110)
        assert pat.doji([c]) is None


class TestHammer:
    def test_hammer_detected(self):
        # Small body at top, long lower shadow, minimal upper shadow
        c = _candle(100, 100.5, 95, 100.2)
        result = pat.hammer([c])
        assert result is not None
        assert result["pattern"] == "hammer"
        assert result["type"] == "bullish"

    def test_no_hammer(self):
        c = _candle(100, 105, 95, 102)
        assert pat.hammer([c]) is None


class TestShootingStar:
    def test_shooting_star_detected(self):
        # Small body at bottom, long upper shadow, minimal lower shadow
        c = _candle(100, 108, 99.5, 100.2)
        result = pat.shooting_star([c])
        assert result is not None
        assert result["type"] == "bearish"


class TestEngulfing:
    def test_bullish_engulfing(self):
        c1 = _candle(105, 106, 99, 100)  # bearish
        c2 = _candle(99, 107, 98, 106)    # bullish, engulfs c1
        result = pat.engulfing([c1, c2])
        assert result is not None
        assert result["pattern"] == "bullish_engulfing"
        assert result["type"] == "bullish"

    def test_bearish_engulfing(self):
        c1 = _candle(100, 107, 99, 106)  # bullish
        c2 = _candle(106, 108, 98, 99)  # bearish, engulfs c1
        result = pat.engulfing([c1, c2])
        assert result is not None
        assert result["type"] == "bearish"


class TestHarami:
    def test_bullish_harami(self):
        c1 = _candle(110, 115, 95, 96)   # big bearish
        c2 = _candle(97, 100, 95, 99)   # small bullish inside
        result = pat.harami([c1, c2])
        assert result is not None
        assert result["type"] == "bullish"


class TestMorningStar:
    def test_morning_star_detected(self):
        c1 = _candle(110, 112, 108, 108)  # bearish
        c2 = _candle(107, 108, 106, 107)  # small body
        c3 = _candle(107, 112, 106, 111)  # bullish, closes above c1 mid
        result = pat.morning_star([c1, c2, c3])
        assert result is not None
        assert result["pattern"] == "morning_star"
        assert result["type"] == "bullish"


class TestEveningStar:
    def test_evening_star_detected(self):
        c1 = _candle(100, 105, 99, 104)   # bullish
        c2 = _candle(104, 105, 103, 104)  # small body
        c3 = _candle(104, 104, 96, 97)    # bearish, closes below c1 mid
        result = pat.evening_star([c1, c2, c3])
        assert result is not None
        assert result["type"] == "bearish"


class TestThreeWhiteSoldiers:
    def test_three_white_soldiers(self):
        c1 = _candle(100, 103, 99, 102)
        c2 = _candle(102, 105, 101, 104)
        c3 = _candle(104, 107, 103, 106)
        result = pat.three_white_soldiers([c1, c2, c3])
        assert result is not None
        assert result["type"] == "bullish"


class TestThreeBlackCrows:
    def test_three_black_crows(self):
        c1 = _candle(110, 111, 106, 107)
        c2 = _candle(107, 108, 103, 104)
        c3 = _candle(104, 105, 100, 101)
        result = pat.three_black_crows([c1, c2, c3])
        assert result is not None
        assert result["type"] == "bearish"


class TestBreakout:
    def test_breakout_bullish(self):
        # 20 candles in range 100-105, then breakout to 110
        candles = [_candle(100, 105, 99, 102) for _ in range(20)]
        candles.append(_candle(102, 111, 101, 110))
        result = pat.breakout(candles, lookback=20)
        assert result is not None
        assert result["type"] == "bullish"

    def test_breakout_bearish(self):
        candles = [_candle(100, 105, 99, 102) for _ in range(20)]
        candles.append(_candle(102, 103, 93, 94))
        result = pat.breakout(candles, lookback=20)
        assert result is not None
        assert result["type"] == "bearish"


class TestDetectPatterns:
    def test_detect_returns_list(self):
        candles = [_candle(100, 105, 99, 102) for _ in range(25)]
        result = pat.detect_patterns(candles)
        assert isinstance(result, list)

    def test_detect_finds_patterns(self):
        c1 = _candle(110, 115, 95, 96)
        c2 = _candle(97, 100, 95, 99)
        c3 = _candle(99, 105, 98, 104)
        result = pat.detect_patterns([c1, c2, c3])
        assert len(result) > 0
