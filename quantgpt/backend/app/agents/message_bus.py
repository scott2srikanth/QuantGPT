"""MessageBus — inter-agent communication backed by the `messages` table.

Agents publish and consume messages addressed to a specific agent or
broadcast on a topic. Messages persist until delivered, so agents can
communicate across runs and across process restarts.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.models import Message


class MessageBus:
    """Durable pub/sub message bus for inter-agent communication."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def publish(
        self,
        *,
        from_agent_id: uuid.UUID | None,
        to_agent_id: uuid.UUID | None,
        topic: str,
        payload: dict[str, Any] | None = None,
    ) -> uuid.UUID:
        msg = Message(
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            topic=topic,
            payload=payload or {},
            delivered=False,
        )
        self._db.add(msg)
        self._db.commit()
        self._db.refresh(msg)
        return msg.id

    def consume(self, agent_id: uuid.UUID, *, limit: int = 50) -> list[Message]:
        """Fetch and mark delivered up to `limit` undelivered messages for agent_id."""
        rows = list(
            self._db.scalars(
                select(Message)
                .where(Message.to_agent_id == agent_id, Message.delivered.is_(False))
                .order_by(Message.created_at.asc())
                .limit(limit)
            ).all()
        )
        if rows:
            ids = [r.id for r in rows]
            self._db.execute(
                update(Message).where(Message.id.in_(ids)).values(delivered=True, delivered_at=datetime.now(timezone.utc))
            )
            self._db.commit()
        return rows

    def consume_topic(self, topic: str, *, limit: int = 50) -> list[Message]:
        """Fetch undelivered broadcast messages for a topic (to_agent_id is null)."""
        rows = list(
            self._db.scalars(
                select(Message)
                .where(Message.topic == topic, Message.to_agent_id.is_(None), Message.delivered.is_(False))
                .order_by(Message.created_at.asc())
                .limit(limit)
            ).all()
        )
        if rows:
            ids = [r.id for r in rows]
            self._db.execute(
                update(Message).where(Message.id.in_(ids)).values(delivered=True, delivered_at=datetime.now(timezone.utc))
            )
            self._db.commit()
        return rows

    def pending_count(self, agent_id: uuid.UUID | None = None) -> int:
        q = select(Message).where(Message.delivered.is_(False))
        if agent_id is not None:
            q = q.where(Message.to_agent_id == agent_id)
        return len(list(self._db.scalars(q).all()))
