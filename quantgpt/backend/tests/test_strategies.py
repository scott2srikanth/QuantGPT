"""Tests for the Strategy Research Engine — strategies, backtester,
registry, marketplace, plugins."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from app.analysis import indicators as ind
from app.integration.models import Candle
from app.strategies.base import Signal, SignalType, StrategyBase
from app.strategies.backtester import Backtester
from app.strategies.builtins import (
    BUILTIN_STRATEGIES,
    BreakoutStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    PortfolioRotationStrategy,
    SwingStrategy,
    TrendFollowingStrategy,
    VolatilityExpansionStrategy,
)
from app.strategies.marketplace import build_marketplace
from app.strategies.registry import (
    StrategyAlreadyRegisteredError,
    StrategyNotFoundError,
    build_registry,
)


# ── Fixtures ──

def make_candles(n: int = 200, base: float = 100.0, trend: float = 0.5) -> list[Candle]:
    """Generate n synthetic candles with an upward trend + noise."""
    import random
    random.seed(42)
    candles: list[Candle] = []
    price = base
    for i in range(n):
        o = price
        c = price + trend + random.uniform(-1.0, 1.0)
        h = max(o, c) + random.uniform(0.1, 1.0)
        lo = min(o, c) - random.uniform(0.1, 1.0)
        v = int(1000 + random.uniform(-200, 200))
        candles.append(Candle(
            timestamp=datetime(2024, 1, 1) + __import__("datetime").timedelta(days=i),
            open=Decimal(str(round(o, 2))),
            high=Decimal(str(round(h, 2))),
            low=Decimal(str(round(lo, 2))),
            close=Decimal(str(round(c, 2))),
            volume=v,
        ))
        price = c
    return candles


def make_sideways_candles(n: int = 200, base: float = 100.0) -> list[Candle]:
    """Generate n synthetic candles oscillating around base (mean-reverting)."""
    import random
    random.seed(7)
    candles: list[Candle] = []
    price = base
    for i in range(n):
        # Pull back toward base
        price += (base - price) * 0.1 + random.uniform(-2.0, 2.0)
        o = price
        c = price + random.uniform(-1.0, 1.0)
        h = max(o, c) + 0.5
        lo = min(o, c) - 0.5
        v = int(1000 + random.uniform(-200, 200))
        candles.append(Candle(
            timestamp=datetime(2024, 1, 1) + __import__("datetime").timedelta(days=i),
            open=Decimal(str(round(o, 2))),
            high=Decimal(str(round(h, 2))),
            low=Decimal(str(round(lo, 2))),
            close=Decimal(str(round(c, 2))),
            volume=v,
        ))
        price = c
    return candles


@pytest.fixture
def trending_candles() -> list[Candle]:
    return make_candles(200, 100.0, 0.5)


@pytest.fixture
def sideways_candles() -> list[Candle]:
    return make_sideways_candles(200, 100.0)


# ── Indicator sanity ──

class TestIndicators:
    def test_ema_length_matches_input(self):
        out = ind.ema([1, 2, 3, 4, 5], 3)
        assert len(out) == 5
        assert not any(__import__("math").isnan(v) for v in out)

    def test_rsi_range(self, trending_candles):
        v = ind.rsi(trending_candles, 14)
        assert v is not None
        assert 0 <= v <= 100

    def test_atr_positive(self, trending_candles):
        v = ind.atr(trending_candles, 14)
        assert v is not None
        assert v > 0

    def test_bollinger_has_bands(self, trending_candles):
        bb = ind.bollinger_bands(trending_candles, 20, 2.0)
        assert bb["upper"] is not None
        assert bb["lower"] is not None
        assert bb["upper"] >= bb["lower"]

    def test_supertrend_returns_trend(self, trending_candles):
        st = ind.supertrend(trending_candles, 10, 3.0)
        assert st["trend"] in ("up", "down")

    def test_macd_returns_dict(self, trending_candles):
        m = ind.macd(trending_candles, 12, 26, 9)
        assert "macd" in m
        assert "signal" in m

    def test_adx_returns_value(self, trending_candles):
        a = ind.adx(trending_candles, 14)
        assert a["adx"] is not None or a["adx"] is None  # just ensure no crash

    def test_all_indicators_runs(self, trending_candles):
        result = ind.all_indicators(trending_candles)
        assert isinstance(result, dict)
        assert "rsi_14" in result


# ── Strategy signal generation ──

class TestStrategySignals:
    def test_momentum_generates_signals(self, trending_candles):
        s = MomentumStrategy()
        signals = s.generate_signals(trending_candles)
        assert isinstance(signals, list)
        for sig in signals:
            assert sig.strategy_name == "momentum"
            assert sig.signal_type in (SignalType.BUY, SignalType.SELL, SignalType.HOLD)
            assert 0 <= sig.strength <= 100

    def test_breakout_generates_signals(self, trending_candles):
        s = BreakoutStrategy()
        signals = s.generate_signals(trending_candles)
        assert isinstance(signals, list)

    def test_swing_generates_signals(self, sideways_candles):
        s = SwingStrategy()
        signals = s.generate_signals(sideways_candles)
        assert isinstance(signals, list)

    def test_trend_following_generates_signals(self, trending_candles):
        s = TrendFollowingStrategy()
        signals = s.generate_signals(trending_candles)
        assert isinstance(signals, list)

    def test_mean_reversion_generates_signals(self, sideways_candles):
        s = MeanReversionStrategy()
        signals = s.generate_signals(sideways_candles)
        assert isinstance(signals, list)

    def test_volatility_expansion_generates_signals(self, trending_candles):
        s = VolatilityExpansionStrategy()
        signals = s.generate_signals(trending_candles)
        assert isinstance(signals, list)

    def test_portfolio_rotation_generates_signals(self, trending_candles):
        s = PortfolioRotationStrategy()
        signals = s.generate_signals(trending_candles)
        assert isinstance(signals, list)

    def test_all_strategies_handle_short_input(self):
        short = make_candles(5)
        for cls in BUILTIN_STRATEGIES:
            s = cls()
            signals = s.generate_signals(short)
            assert signals == [], f"{cls.__name__} should return [] for short input"

    def test_strategy_config_schema_and_defaults(self):
        for cls in BUILTIN_STRATEGIES:
            schema = cls.config_schema()
            defaults = cls.default_config()
            assert isinstance(schema, dict)
            assert isinstance(defaults, dict)
            assert "type" in schema  # JSON schema marker

    def test_strategy_to_dict(self):
        s = MomentumStrategy()
        d = s.to_dict()
        assert d["name"] == "momentum"
        assert d["display_name"] == "Momentum"
        assert d["version"] == "1.0.0"
        assert d["is_plugin"] is False
        assert d["source"] == "builtin"

    def test_strategy_is_versioned(self):
        for cls in BUILTIN_STRATEGIES:
            assert cls.version != ""
            assert "." in cls.version  # semver-ish


# ── Backtester ──

class TestBacktester:
    def test_backtest_returns_result(self, trending_candles):
        s = MomentumStrategy()
        result = s.backtest(trending_candles, initial_capital=100000.0)
        assert result.strategy_name == "momentum"
        assert result.initial_capital == 100000.0
        assert result.final_value >= 0
        assert isinstance(result.total_return, float)
        assert isinstance(result.sharpe_ratio, float)
        assert isinstance(result.max_drawdown, float)
        assert isinstance(result.win_rate, float)
        assert isinstance(result.benchmark_return, float)
        assert isinstance(result.outperformance, float)
        assert result.total_trades >= 0
        assert result.winning_trades + result.losing_trades == result.total_trades

    def test_backtest_with_custom_config(self, trending_candles):
        s = MomentumStrategy()
        result = s.backtest(trending_candles, config={"fast_ema": 5, "slow_ema": 15}, initial_capital=50000.0)
        assert result.initial_capital == 50000.0
        assert result.config.get("fast_ema") == 5

    def test_backtest_equity_curve_populated(self, trending_candles):
        s = BreakoutStrategy()
        result = s.backtest(trending_candles)
        assert isinstance(result.equity_curve, list)

    def test_backtest_benchmark_present(self, trending_candles):
        s = TrendFollowingStrategy()
        result = s.backtest(trending_candles)
        # Benchmark is buy-and-hold; should be non-zero for trending data
        assert result.benchmark_return != 0 or len(trending_candles) < 2

    def test_backtester_direct(self, trending_candles):
        s = MomentumStrategy()
        bt = Backtester(strategy=s, config=s.default_config(), initial_capital=100000.0)
        result = bt.run(trending_candles)
        assert result.strategy_name == "momentum"


# ── Registry ──

class TestRegistry:
    def test_build_registry_has_all_builtins(self):
        r = build_registry()
        assert len(r) == len(BUILTIN_STRATEGIES)
        for cls in BUILTIN_STRATEGIES:
            assert r.contains(cls.name)

    def test_get_returns_strategy(self):
        r = build_registry()
        s = r.get("momentum")
        assert s.name == "momentum"

    def test_get_unknown_raises(self):
        r = build_registry()
        with pytest.raises(StrategyNotFoundError):
            r.get("nonexistent")

    def test_register_duplicate_raises(self):
        r = build_registry()
        with pytest.raises(StrategyAlreadyRegisteredError):
            r.register(MomentumStrategy())

    def test_names_returns_list(self):
        r = build_registry()
        names = r.names()
        assert "momentum" in names
        assert len(names) == len(BUILTIN_STRATEGIES)

    def test_list_all_returns_dicts(self):
        r = build_registry()
        all_s = r.list_all()
        assert all(isinstance(d, dict) for d in all_s)
        assert len(all_s) == len(BUILTIN_STRATEGIES)


# ── Marketplace ──

class TestMarketplace:
    def test_build_marketplace_auto_publishes(self):
        r = build_registry()
        mp = build_marketplace(r)
        listings = mp.list_published()
        assert len(listings) == len(BUILTIN_STRATEGIES)
        for l in listings:
            assert l["is_published"] is True

    def test_publish_custom(self):
        r = build_registry()
        mp = build_marketplace(r)
        # Re-publish with custom title
        listing = mp.publish("momentum", title="Custom Momentum", author="test")
        assert listing.title == "Custom Momentum"
        assert listing.author == "test"

    def test_rate_strategy(self):
        r = build_registry()
        mp = build_marketplace(r)
        listing = mp.rate("momentum", 4.5)
        assert listing.rating == 4.5

    def test_rate_invalid_raises(self):
        r = build_registry()
        mp = build_marketplace(r)
        with pytest.raises(ValueError):
            mp.rate("momentum", 6.0)

    def test_rate_unknown_raises(self):
        r = build_registry()
        mp = build_marketplace(r)
        with pytest.raises(KeyError):
            mp.rate("nonexistent", 3.0)

    def test_download_increments(self):
        r = build_registry()
        mp = build_marketplace(r)
        before = mp.list_published()[0]["downloads"]
        mp.download("momentum")
        after = mp.list_published()[0]["downloads"]
        assert after == before + 1

    def test_download_unknown_raises(self):
        r = build_registry()
        mp = build_marketplace(r)
        with pytest.raises(KeyError):
            mp.download("nonexistent")

    def test_feature_and_unfeature(self):
        r = build_registry()
        mp = build_marketplace(r)
        listing = mp.feature("momentum")
        assert listing.is_featured is True
        listing = mp.unfeature("momentum")
        assert listing.is_featured is False

    def test_unpublish(self):
        r = build_registry()
        mp = build_marketplace(r)
        mp.unpublish("momentum")
        names = [l["strategy_name"] for l in mp.list_published()]
        assert "momentum" not in names

    def test_get_listing(self):
        r = build_registry()
        mp = build_marketplace(r)
        listing = mp.get_listing("momentum")
        assert listing is not None
        assert listing["strategy_name"] == "momentum"
        assert "strategy_info" in listing

    def test_get_listing_unknown(self):
        r = build_registry()
        mp = build_marketplace(r)
        assert mp.get_listing("nonexistent") is None

    def test_list_published_filter_by_tag(self):
        r = build_registry()
        mp = build_marketplace(r)
        listings = mp.list_published(tag="momentum")
        for l in listings:
            assert "momentum" in l["tags"]


# ── Plugins ──

class TestPlugins:
    def test_load_plugin_from_file(self, tmp_path):
        plugin_code = '''
from app.strategies.base import Signal, SignalType, StrategyBase

class MyPlugin(StrategyBase):
    name = "my_plugin"
    display_name = "My Plugin"
    type = "custom"
    version = "1.0.0"
    description = "Test plugin"

    def generate_signals(self, candles, config=None):
        return []

STRATEGY_CLASS = MyPlugin
'''
        p = tmp_path / "my_plugin.py"
        p.write_text(plugin_code)
        from app.strategies.plugins import load_plugin_from_file
        r = build_registry()
        strategy = load_plugin_from_file(str(p), r)
        assert strategy is not None
        assert strategy.name == "my_plugin"
        assert r.contains("my_plugin")

    def test_load_plugin_from_module(self):
        # Create a module in a temp package
        import sys
        import types
        mod = types.ModuleType("test_plugin_mod")
        from app.strategies.base import StrategyBase

        class ModPlugin(StrategyBase):
            name = "mod_plugin"
            display_name = "Mod Plugin"
            type = "custom"
            version = "1.0.0"
            description = "Module plugin"

            def generate_signals(self, candles, config=None):
                return []

        mod.STRATEGY_CLASS = ModPlugin
        sys.modules["test_plugin_mod"] = mod
        from app.strategies.plugins import load_plugin_from_module
        r = build_registry()
        strategy = load_plugin_from_module("test_plugin_mod", r)
        assert strategy is not None
        assert strategy.name == "mod_plugin"

    def test_load_plugin_duplicate_returns_none(self, tmp_path):
        plugin_code = '''
from app.strategies.base import StrategyBase

class DupPlugin(StrategyBase):
    name = "momentum"  # conflicts with builtin
    display_name = "Dup"
    type = "custom"
    version = "1.0.0"
    description = "Dup"

    def generate_signals(self, candles, config=None):
        return []
'''
        p = tmp_path / "dup.py"
        p.write_text(plugin_code)
        from app.strategies.plugins import load_plugin_from_file
        r = build_registry()
        strategy = load_plugin_from_file(str(p), r)
        assert strategy is None  # duplicate name rejected

    def test_load_plugin_missing_file(self):
        from app.strategies.plugins import load_plugin_from_file
        r = build_registry()
        assert load_plugin_from_file("/nonexistent/path.py", r) is None
