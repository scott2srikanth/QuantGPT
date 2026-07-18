"""AgentMemory — per-agent key/value store backed by the `agent_memory` table.

Each agent stores arbitrary JSON values keyed by string. Used for state that
must survive across runs (learned parameters, last-seen values, caches).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import AgentMemory


class Memory:
    """Key/value memory for a single agent, persisted to Supabase."""

    def __init__(self, agent_id: uuid.UUID, db: Session) -> None:
        self._agent_id = agent_id
        self._db = db

    def get(self, key: str, default: Any = None) -> Any:
        row = self._db.scalar(
            select(AgentMemory).where(AgentMemory.agent_id == self._agent_id, AgentMemory.key == key)
        )
        return row.value if row else default

    def set(self, key: str, value: Any) -> None:
        row = self._db.scalar(
            select(AgentMemory).where(AgentMemory.agent_id == self._agent_id, AgentMemory.key == key)
        )
        if row:
            row.value = value
        else:
            self._db.add(AgentMemory(agent_id=self._agent_id, key=key, value=value))
        self._db.commit()

    def delete(self, key: str) -> None:
        row = self._db.scalar(
            select(AgentMemory).where(AgentMemory.agent_id == self._agent_id, AgentMemory.key == key)
        )
        if row:
            self._db.delete(row)
            self._db.commit()

    def all(self) -> dict[str, Any]:
        rows = self._db.scalars(
            select(AgentMemory).where(AgentMemory.agent_id == self._agent_id)
        ).all()
        return {r.key: r.value for r in rows}

    def clear(self) -> None:
        rows = self._db.scalars(
            select(AgentMemory).where(AgentMemory.agent_id == self._agent_id)
        ).all()
        for r in rows:
            self._db.delete(r)
        self._db.commit()
