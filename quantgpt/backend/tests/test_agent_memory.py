"""Tests for Memory."""

from __future__ import annotations

from app.agents.memory import Memory
from app.models import models


def test_set_get(db, agent_row):
    m = Memory(agent_row.id, db)
    m.set("k1", {"v": 1})
    assert m.get("k1") == {"v": 1}


def test_get_missing_returns_default(db, agent_row):
    m = Memory(agent_row.id, db)
    assert m.get("missing") is None
    assert m.get("missing", "fallback") == "fallback"


def test_set_overwrites(db, agent_row):
    m = Memory(agent_row.id, db)
    m.set("k", 1)
    m.set("k", 2)
    assert m.get("k") == 2


def test_delete(db, agent_row):
    m = Memory(agent_row.id, db)
    m.set("k", 1)
    m.delete("k")
    assert m.get("k") is None


def test_all(db, agent_row):
    m = Memory(agent_row.id, db)
    m.set("a", 1)
    m.set("b", 2)
    assert m.all() == {"a": 1, "b": 2}


def test_clear(db, agent_row):
    m = Memory(agent_row.id, db)
    m.set("a", 1)
    m.set("b", 2)
    m.clear()
    assert m.all() == {}


def test_isolation_per_agent(db):
    a1 = models.Agent(name="a1", type="t", config={})
    a2 = models.Agent(name="a2", type="t", config={})
    db.add_all([a1, a2])
    db.commit()
    db.refresh(a1)
    db.refresh(a2)
    Memory(a1.id, db).set("k", "agent1")
    Memory(a2.id, db).set("k", "agent2")
    assert Memory(a1.id, db).get("k") == "agent1"
    assert Memory(a2.id, db).get("k") == "agent2"
