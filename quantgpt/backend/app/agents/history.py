"""History — per-agent execution history backed by `agent_history`.

Every run() invocation records a history row with status, result, duration,
and error (if any). Used for audit, debugging, and the self-evaluation agent.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import AgentHistory


class HistoryStore:
    """Persists and retrieves agent execution history."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def record(
        self,
        *,
        agent_id: uuid.UUID,
        run_id: uuid.UUID,
        status: str,
        result: dict[str, Any] | None = None,
        duration_ms: int | None = None,
        error: str | None = None,
    ) -> AgentHistory:
        row = AgentHistory(
            agent_id=agent_id,
            run_id=run_id,
            status=status,
            result=result or {},
            duration_ms=duration_ms,
            error=error,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc) if status in ("completed", "failed") else None,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_by_agent(self, agent_id: uuid.UUID, *, limit: int = 50) -> list[AgentHistory]:
        return list(
            self._db.scalars(
                select(AgentHistory).where(AgentHistory.agent_id == agent_id).order_by(AgentHistory.started_at.desc()).limit(limit)
            ).all()
        )

    def latest(self, agent_id: uuid.UUID) -> AgentHistory | None:
        return self._db.scalar(
            select(AgentHistory)
            .where(AgentHistory.agent_id == agent_id)
            .order_by(AgentHistory.started_at.desc())
            .limit(1)
        )
