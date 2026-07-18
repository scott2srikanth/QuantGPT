"""AgentHealth — records and retrieves health snapshots for agents.

Each agent reports a health status (healthy/degraded/unhealthy) which is
persisted to the `agent_health` table. The manager uses this to surface
aggregate system health and to decide whether to route tasks to an agent.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import AgentHealth

HealthStatus = Literal["healthy", "degraded", "unhealthy"]


class HealthTracker:
    """Persists agent health snapshots."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def record(self, agent_id: uuid.UUID, status: HealthStatus, detail: str | None = None) -> None:
        self._db.add(AgentHealth(agent_id=agent_id, status=status, detail=detail, checked_at=datetime.now(timezone.utc)))
        self._db.commit()

    def latest(self, agent_id: uuid.UUID) -> AgentHealth | None:
        return self._db.scalar(
            select(AgentHealth)
            .where(AgentHealth.agent_id == agent_id)
            .order_by(AgentHealth.checked_at.desc())
            .limit(1)
        )

    def all_latest(self) -> list[AgentHealth]:
        """Return the most recent health row per agent."""
        rows = list(
            self._db.scalars(
                select(AgentHealth).order_by(AgentHealth.checked_at.desc())
            ).all()
        )
        seen: set[uuid.UUID] = set()
        out: list[AgentHealth] = []
        for r in rows:
            if r.agent_id not in seen:
                seen.add(r.agent_id)
                out.append(r)
        return out
