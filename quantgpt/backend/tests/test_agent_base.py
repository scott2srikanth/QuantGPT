"""Tests for AgentBase — run/status/metrics/health/config/memory/history + retry."""

from __future__ import annotations

import pytest

from app.agents.base import AgentBase
from app.agents.exceptions import TaskMaxAttemptsExceededError


class _OkAgent(AgentBase):
    name = "ok_agent"
    type = "test"

    def execute(self, payload):
        return {"ok": True, "echo": payload}


class _FailAgent(AgentBase):
    name = "fail_agent"
    type = "test"

    def __init__(self, *, agent_id, db, fail_times=0, **kw):
        super().__init__(agent_id=agent_id, db=db, **kw)
        self._calls = 0
        self._fail_times = fail_times

    def execute(self, payload):
        self._calls += 1
        if self._calls <= self._fail_times:
            raise RuntimeError(f"transient failure {self._calls}")
        return {"recovered_after": self._calls}


class _AlwaysFailAgent(AgentBase):
    name = "always_fail_agent"
    type = "test"

    def execute(self, payload):
        raise RuntimeError("permanent failure")


def _make(db, cls, **kw):
    from app.models import models

    cfg = kw.pop("config", {})
    row = models.Agent(name=cls.name, type=cls.type, config=cfg)
    db.add(row)
    db.commit()
    db.refresh(row)
    return cls(agent_id=row.id, db=db, config=cfg, **kw)


def test_run_success(db):
    a = _make(db, _OkAgent)
    result = a.run({"input": 1})
    assert result["status"] == "completed"
    assert result["result"]["ok"] is True
    assert result["attempts"] == 1


def test_status(db):
    a = _make(db, _OkAgent)
    s = a.status()
    assert s["name"] == "ok_agent"
    assert s["status"] == "idle"
    assert s["running"] is False


def test_config(db):
    a = _make(db, _OkAgent, config={"threshold": 0.5})
    c = a.config()
    assert c["config"]["threshold"] == 0.5


def test_memory(db):
    a = _make(db, _OkAgent)
    a._memory.set("learned", {"param": 1})
    mem = a.memory()
    assert mem["learned"]["param"] == 1


def test_history(db):
    a = _make(db, _OkAgent)
    a.run({"x": 1})
    h = a.history()
    assert len(h) == 1
    assert h[0].status == "completed"


def test_metrics(db):
    a = _make(db, _OkAgent)
    a.run({})
    m = a.metrics()
    assert "duration_ms" in m
    assert m["attempts"] == 1.0


def test_health_default_healthy(db):
    a = _make(db, _OkAgent)
    a.run({})
    h = a.health()
    assert h["status"] == "healthy"


def test_retry_then_succeed(db):
    a = _make(db, _FailAgent, fail_times=2, max_attempts=3)
    result = a.run({})
    assert result["status"] == "completed"
    assert result["attempts"] == 3  # 2 failures + 1 success


def test_retry_exhausted_raises(db):
    a = _make(db, _AlwaysFailAgent, max_attempts=2)
    with pytest.raises(TaskMaxAttemptsExceededError):
        a.run({})
    # status should be error
    assert a.status()["status"] == "error"
    # history should have a failed row
    h = a.history()
    assert any(r.status == "failed" for r in h)


def test_health_unhealthy_after_failure(db):
    a = _make(db, _AlwaysFailAgent, max_attempts=1)
    with pytest.raises(TaskMaxAttemptsExceededError):
        a.run({})
    h = a.health()
    assert h["status"] == "unhealthy"
