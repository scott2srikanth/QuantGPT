"""Tests for the placeholder agents."""

from __future__ import annotations

from app.agents.agents import ALL_AGENT_CLASSES
from app.agents.factory import build_agent_framework
from app.config.settings import Settings


def _settings():
    return Settings(  # type: ignore[call-arg]
        quantgpt_jwt_secret="test-secret-not-used-here",
        quantgpt_admin_email="admin@test.local",
        quantgpt_admin_password="ChangeMe123!",
        database_url="sqlite:///:memory:",
    )


def test_all_15_agents_present():
    assert len(ALL_AGENT_CLASSES) == 15
    names = [c.name for c in ALL_AGENT_CLASSES]
    expected = [
        "market_scanner", "technical_analysis", "fundamental_analysis", "news",
        "risk", "portfolio", "strategy", "trade_decision", "backtesting",
        "prediction", "self_evaluation", "reporting", "trade_journal",
        "monitoring", "alerting",
    ]
    assert names == expected


def test_each_placeholder_runs(db):
    s = _settings()
    manager, _ = build_agent_framework(db, s)
    for cls in ALL_AGENT_CLASSES:
        result = manager.run_agent(cls.name, {"test": True})
        assert result["status"] == "completed"
        assert result["result"]["status"] == "placeholder"
        assert result["result"]["agent"] == cls.name


def test_each_placeholder_returns_status(db):
    s = _settings()
    manager, _ = build_agent_framework(db, s)
    for cls in ALL_AGENT_CLASSES:
        st = manager.get(cls.name).status()
        assert st["name"] == cls.name
        assert st["type"] == cls.type
