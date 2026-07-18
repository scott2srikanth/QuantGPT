"""Tests for MessageBus."""

from __future__ import annotations

from app.agents.message_bus import MessageBus


def test_publish_and_consume(db, agent_row):
    bus = MessageBus(db)
    msg_id = bus.publish(from_agent_id=None, to_agent_id=agent_row.id, topic="scan", payload={"v": 1})
    msgs = bus.consume(agent_row.id)
    assert len(msgs) == 1
    assert msgs[0].topic == "scan"
    assert msgs[0].payload == {"v": 1}
    assert msgs[0].delivered is True


def test_consume_marks_delivered(db, agent_row):
    bus = MessageBus(db)
    bus.publish(from_agent_id=None, to_agent_id=agent_row.id, topic="t")
    bus.consume(agent_row.id)
    assert bus.pending_count(agent_row.id) == 0


def test_consume_topic_broadcast(db, agent_row):
    bus = MessageBus(db)
    bus.publish(from_agent_id=None, to_agent_id=None, topic="broadcast", payload={"x": 1})
    msgs = bus.consume_topic("broadcast")
    assert len(msgs) == 1
    assert msgs[0].topic == "broadcast"


def test_pending_count(db, agent_row):
    bus = MessageBus(db)
    bus.publish(from_agent_id=None, to_agent_id=agent_row.id, topic="t")
    bus.publish(from_agent_id=None, to_agent_id=agent_row.id, topic="t")
    assert bus.pending_count(agent_row.id) == 2
