"""Tests for AgentRegistry and AgentManager."""

from __future__ import annotations

import pytest

from app.agents.agents import ALL_AGENT_CLASSES
from app.agents.exceptions import AgentAlreadyRegisteredError, AgentNotFoundError
from app.agents.factory import build_agent_framework
from app.agents.manager import AgentManager
from app.agents.registry import AgentRegistry
from app.agents.scheduler import Scheduler
from app.config.settings import Settings
from app.models import models


def _settings():
    return Settings(  # type: ignore[call-arg]
        quantgpt_jwt_secret="test-secret-not-used-here",
        quantgpt_admin_email="admin@test.local",
        quantgpt_admin_password="ChangeMe123!",
        database_url="sqlite:///:memory:",
    )


def test_registry_register_and_get(db):
    from app.agents.base import AgentBase

    class _A(AgentBase):
        name = "a"
        type = "t"

        def execute(self, payload):
            return {}

    row = models.Agent(name="a", type="t", config={})
    db.add(row)
    db.commit()
    db.refresh(row)
    a = _A(agent_id=row.id, db=db)
    r = AgentRegistry()
    r.register(a)
    assert r.get("a") is a
    assert "a" in r.names()
    assert len(r) == 1


def test_registry_duplicate_raises(db):
    from app.agents.base import AgentBase

    class _A(AgentBase):
        name = "dup"
        type = "t"

        def execute(self, payload):
            return {}

    row = models.Agent(name="dup", type="t", config={})
    db.add(row)
    db.commit()
    db.refresh(row)
    a = _A(agent_id=row.id, db=db)
    r = AgentRegistry()
    r.register(a)
    with pytest.raises(AgentAlreadyRegisteredError):
        r.register(a)


def test_registry_missing_raises():
    r = AgentRegistry()
    with pytest.raises(AgentNotFoundError):
        r.get("nope")


def test_factory_registers_all_15_agents(db):
    s = _settings()
    manager, scheduler = build_agent_framework(db, s)
    names = manager.all_agents().keys()
    assert len(names) == 15
    for cls in ALL_AGENT_CLASSES:
        assert cls.name in names


def test_factory_all_agents_expose_uniform_interface(db):
    s = _settings()
    manager, _ = build_agent_framework(db, s)
    for name, agent in manager.all_agents().items():
        # every agent must expose all 8 methods
        for method in ("run", "status", "metrics", "health", "config", "memory", "history"):
            assert hasattr(agent, method), f"{name} missing {method}"


def test_run_agent_immediate(db):
    s = _settings()
    manager, _ = build_agent_framework(db, s)
    result = manager.run_agent("market_scanner", {"symbol": "RELIANCE"})
    assert result["status"] == "completed"
    assert result["result"]["agent"] == "market_scanner"


def test_enqueue_and_drain(db):
    s = _settings()
    manager, _ = build_agent_framework(db, s)
    manager.enqueue_task("risk", {"check": "volatility"}, max_attempts=1)
    assert manager._queue.pending_count() == 1
    executed = manager.drain(limit=10)
    assert executed == 1
    assert manager._queue.pending_count() == 0


def test_send_and_deliver_message(db):
    s = _settings()
    manager, _ = build_agent_framework(db, s)
    manager.send_message(from_agent_name="news", to_agent_name="risk", topic="alert", payload={"msg": "hi"})
    delivered = manager.deliver_messages()
    assert delivered == 1
    risk = manager.get("risk")
    # message should be stored in risk agent's memory
    mem = risk.memory()
    assert any("alert" in k for k in mem)


def test_system_health(db):
    s = _settings()
    manager, _ = build_agent_framework(db, s)
    h = manager.system_health()
    assert h["total_agents"] == 15
    assert h["healthy"] == 15  # no runs yet -> default healthy
    assert h["pending_tasks"] == 0


def test_scheduler_tick(db):
    s = _settings()
    manager, _ = build_agent_framework(db, s)
    scheduler = Scheduler(manager, interval_seconds=0.01)
    manager.enqueue_task("monitoring", {"x": 1}, max_attempts=1)
    result = scheduler.tick()
    assert result["executed_tasks"] == 1
