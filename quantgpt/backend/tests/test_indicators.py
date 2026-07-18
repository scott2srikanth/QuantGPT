"""Tests for the indicator library."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.analysis import indicators as ind
from app.integration.models import Candle


def _candles(prices: list[float], volumes: list[int] | None = None) -> list[Candle]:
    """Build candles from a list of close prices. Open = prev close,
    high/low bracket the close."""
    out: list[Candle] = []
    for i, p in enumerate(prices):
        o = prices[i - 1] if i > 0 else p
        h = max(o, p) * 1.001
        l = min(o, p) * 0.999
        v = volumes[i] if volumes and i < len(volumes) else 1000
        out.append(Candle(
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open=Decimal(str(o)), high=Decimal(str(h)),
            low=Decimal(str(l)), close=Decimal(str(p)), volume=v,
        ))
    return out


class TestEMA:
    def test_ema_basic(self):
        vals = [1, 2, 3, 4, 5]
        result = ind.ema(vals, 3)
        assert len(result) == 5
        assert result[0] == 1.0

    def test_ema_latest(self):
        vals = [1, 2, 3, 4, 5]
        latest = ind.ema_latest(vals, 3)
        assert latest is not None
        assert 4 < latest < 5

    def test_ema_empty(self):
        assert ind.ema([], 5) == []
        assert ind.ema_latest([], 5) is None


class TestSMA:
    def test_sma_basic(self):
        vals = [1, 2, 3, 4, 5]
        result = ind.sma(vals, 3)
        assert len(result) == 5
        assert result[0] != result[0]  # NaN for first 2
        assert result[2] == 2.0
        assert result[3] == 3.0
        assert result[4] == 4.0

    def test_sma_latest(self):
        assert ind.sma_latest([1, 2, 3, 4, 5], 5) == 3.0
        assert ind.sma_latest([1, 2], 5) is None


class TestMACD:
    def test_macd_insufficient(self):
        candles = _candles([1, 2, 3])
        result = ind.macd(candles)
        assert result["macd"] is None

    def test_macd_sufficient(self):
        prices = [100 + i * 0.5 for i in range(30)]
        candles = _candles(prices)
        result = ind.macd(candles)
        assert result["macd"] is not None
        assert result["signal"] is not None
        assert result["histogram"] is not None
        assert "macd_series" in result


class TestRSI:
    def test_rsi_insufficient(self):
        candles = _candles([1, 2, 3])
        assert ind.rsi(candles, 14) is None

    def test_rsi_uptrend(self):
        prices = [100 + i for i in range(30)]
        candles = _candles(prices)
        rsi = ind.rsi(candles, 14)
        assert rsi is not None
        assert rsi > 80  # strong uptrend -> high RSI

    def test_rsi_downtrend(self):
        prices = [100 - i for i in range(30)]
        candles = _candles(prices)
        rsi = ind.rsi(candles, 14)
        assert rsi is not None
        assert rsi < 20  # strong downtrend -> low RSI

    def test_rsi_series(self):
        prices = [100 + i for i in range(30)]
        candles = _candles(prices)
        series = ind.rsi_series(candles, 14)
        assert len(series) > 0


class TestATR:
    def test_atr_insufficient(self):
        candles = _candles([1, 2, 3])
        assert ind.atr(candles, 14) is None

    def test_atr_sufficient(self):
        prices = [100 + i * 0.5 for i in range(30)]
        candles = _candles(prices)
        atr = ind.atr(candles, 14)
        assert atr is not None
        assert atr > 0


class TestVWAP:
    def test_vwap_basic(self):
        candles = _candles([10, 20, 30], volumes=[100, 200, 300])
        vwap = ind.vwap(candles)
        assert vwap is not None
        assert vwap > 0

    def test_vwap_no_volume(self):
        candles = _candles([10, 20, 30], volumes=[0, 0, 0])
        assert ind.vwap(candles) is None


class TestSupertrend:
    def test_supertrend_uptrend(self):
        prices = [100 + i for i in range(20)]
        candles = _candles(prices)
        st = ind.supertrend(candles)
        assert st["trend"] == "up"

    def test_supertrend_downtrend(self):
        prices = [100 - i for i in range(20)]
        candles = _candles(prices)
        st = ind.supertrend(candles)
        assert st["trend"] == "down"

    def test_supertrend_insufficient(self):
        candles = _candles([1, 2, 3])
        st = ind.supertrend(candles)
        assert st["trend"] is None


class TestIchimoku:
    def test_ichimoku_sufficient(self):
        prices = [100 + i * 0.5 for i in range(60)]
        candles = _candles(prices)
        result = ind.ichimoku(candles)
        assert result["tenkan"] is not None
        assert result["kijun"] is not None
        assert result["senkou_a"] is not None
        assert result["senkou_b"] is not None

    def test_ichimoku_insufficient(self):
        candles = _candles([1, 2, 3])
        result = ind.ichimoku(candles)
        assert result["tenkan"] is None


class TestBollingerBands:
    def test_bollinger_sufficient(self):
        prices = [100 + i * 0.1 for i in range(25)]
        candles = _candles(prices)
        bb = ind.bollinger_bands(candles)
        assert bb["upper"] is not None
        assert bb["lower"] is not None
        assert bb["upper"] > bb["middle"] > bb["lower"]
        assert 0 <= bb["percent"] <= 1

    def test_bollinger_insufficient(self):
        candles = _candles([1, 2, 3])
        bb = ind.bollinger_bands(candles)
        assert bb["upper"] is None


class TestDonchian:
    def test_donchian_sufficient(self):
        prices = [100 + i for i in range(25)]
        candles = _candles(prices)
        dc = ind.donchian_channels(candles)
        assert dc["upper"] is not None
        assert dc["lower"] is not None
        assert dc["upper"] >= dc["lower"]

    def test_donchian_insufficient(self):
        candles = _candles([1, 2, 3])
        dc = ind.donchian_channels(candles)
        assert dc["upper"] is None


class TestAllIndicators:
    def test_all_indicators_returns_flat(self):
        prices = [100 + i * 0.5 for i in range(60)]
        candles = _candles(prices)
        result = ind.all_indicators(candles)
        assert "flat" in result
        assert "ema_9" in result["flat"]
        assert "rsi_14" in result["flat"]
        assert "macd_macd" in result["flat"]
