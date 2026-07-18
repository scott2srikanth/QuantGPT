"""Tests for TaskQueue."""

from __future__ import annotations

from app.agents.task_queue import TaskQueue


def test_enqueue_and_dequeue(db, agent_row):
    q = TaskQueue(db)
    t = q.enqueue(agent_id=agent_row.id, payload={"x": 1}, priority=5)
    assert t.status == "pending"
    rows = q.dequeue(limit=10)
    assert len(rows) == 1
    assert rows[0].status == "running"
    assert rows[0].payload == {"x": 1}


def test_priority_ordering(db, agent_row):
    q = TaskQueue(db)
    q.enqueue(agent_id=agent_row.id, payload={"n": "low"}, priority=1)
    q.enqueue(agent_id=agent_row.id, payload={"n": "high"}, priority=10)
    rows = q.dequeue(limit=10)
    assert rows[0].payload["n"] == "high"
    assert rows[1].payload["n"] == "low"


def test_mark_completed(db, agent_row):
    q = TaskQueue(db)
    t = q.enqueue(agent_id=agent_row.id)
    q.dequeue(limit=1)
    q.mark_completed(t.id)
    assert q.get(t.id).status == "completed"


def test_mark_failed_retries_until_max(db, agent_row):
    q = TaskQueue(db)
    t = q.enqueue(agent_id=agent_row.id, max_attempts=2)
    q.dequeue(limit=1)
    q.mark_failed(t.id, "boom")
    # should be back to pending (attempt 1 of 2)
    assert q.get(t.id).status == "pending"
    assert q.get(t.id).attempts == 1
    q.dequeue(limit=1)
    q.mark_failed(t.id, "boom again")
    # now exhausted -> failed
    assert q.get(t.id).status == "failed"
    assert q.get(t.id).attempts == 2


def test_cancel(db, agent_row):
    q = TaskQueue(db)
    t = q.enqueue(agent_id=agent_row.id)
    q.cancel(t.id)
    assert q.get(t.id).status == "cancelled"


def test_pending_count(db, agent_row):
    q = TaskQueue(db)
    q.enqueue(agent_id=agent_row.id)
    q.enqueue(agent_id=agent_row.id)
    assert q.pending_count() == 2
    q.dequeue(limit=10)
    assert q.pending_count() == 0


def test_list_by_agent(db, agent_row):
    q = TaskQueue(db)
    q.enqueue(agent_id=agent_row.id, payload={"i": 1})
    q.enqueue(agent_id=agent_row.id, payload={"i": 2})
    rows = q.list_by_agent(agent_row.id)
    assert len(rows) == 2
