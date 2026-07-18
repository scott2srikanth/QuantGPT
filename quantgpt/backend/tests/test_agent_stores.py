"""Tests for Health, Metrics, and History stores."""

from __future__ import annotations

from app.agents.health import HealthTracker
from app.agents.history import HistoryStore
from app.agents.metrics import MetricsStore
from app.models import models


def test_health_record_and_latest(db, agent_row):
    h = HealthTracker(db)
    h.record(agent_row.id, "degraded", "slow")
    latest = h.latest(agent_row.id)
    assert latest.status == "degraded"
    assert latest.detail == "slow"


def test_health_all_latest(db):
    a1 = models.Agent(name="a1", type="t", config={})
    a2 = models.Agent(name="a2", type="t", config={})
    db.add_all([a1, a2])
    db.commit()
    db.refresh(a1)
    db.refresh(a2)
    h = HealthTracker(db)
    h.record(a1.id, "healthy")
    h.record(a2.id, "unhealthy", "down")
    all_h = h.all_latest()
    assert len(all_h) == 2


def test_metrics_record_and_latest(db, agent_row):
    m = MetricsStore(db)
    m.record(agent_row.id, "latency_ms", 100.0)
    m.record(agent_row.id, "latency_ms", 200.0)
    latest = m.latest(agent_row.id)
    assert latest["latency_ms"] == 200.0


def test_metrics_summary(db, agent_row):
    m = MetricsStore(db)
    m.record(agent_row.id, "latency_ms", 100.0)
    m.record(agent_row.id, "latency_ms", 200.0)
    m.record(agent_row.id, "latency_ms", 300.0)
    s = m.summary(agent_row.id)
    assert s["latency_ms"]["avg"] == 200.0
    assert s["latency_ms"]["min"] == 100.0
    assert s["latency_ms"]["max"] == 300.0
    assert s["latency_ms"]["count"] == 3


def test_history_record_and_list(db, agent_row):
    h = HistoryStore(db)
    import uuid

    run_id = uuid.uuid4()
    h.record(agent_id=agent_row.id, run_id=run_id, status="completed", result={"ok": True}, duration_ms=50)
    rows = h.list_by_agent(agent_row.id)
    assert len(rows) == 1
    assert rows[0].status == "completed"
    assert rows[0].result == {"ok": True}
    assert rows[0].duration_ms == 50


def test_history_latest(db, agent_row):
    h = HistoryStore(db)
    import uuid

    h.record(agent_id=agent_row.id, run_id=uuid.uuid4(), status="completed", result={"r": 1})
    h.record(agent_id=agent_row.id, run_id=uuid.uuid4(), status="failed", result={}, error="boom")
    latest = h.latest(agent_row.id)
    assert latest.status == "failed"
    assert latest.error == "boom"
