"""TaskQueue — durable task queue backed by the `tasks` table.

Tasks are addressed to a specific agent, carry a JSON payload, and have a
retry budget. The queue supports priority ordering and scheduled execution.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.models import Task


class TaskQueue:
    """Durable task queue with priority, scheduling, and retries."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def enqueue(
        self,
        *,
        agent_id: uuid.UUID,
        payload: dict[str, Any] | None = None,
        priority: int = 0,
        max_attempts: int = 3,
        scheduled_for: datetime | None = None,
    ) -> Task:
        task = Task(
            agent_id=agent_id,
            payload=payload or {},
            status="pending",
            priority=priority,
            attempts=0,
            max_attempts=max_attempts,
            scheduled_for=scheduled_for or datetime.now(timezone.utc),
        )
        self._db.add(task)
        self._db.commit()
        self._db.refresh(task)
        return task

    def dequeue(self, *, limit: int = 10) -> list[Task]:
        """Claim up to `limit` due pending tasks (highest priority first)."""
        now = datetime.now(timezone.utc)
        rows = list(
            self._db.scalars(
                select(Task)
                .where(Task.status == "pending", Task.scheduled_for <= now)
                .order_by(Task.priority.desc(), Task.scheduled_for.asc())
                .limit(limit)
            ).all()
        )
        if rows:
            ids = [r.id for r in rows]
            self._db.execute(
                update(Task).where(Task.id.in_(ids)).values(status="running", started_at=now)
            )
            self._db.commit()
            for r in rows:
                r.status = "running"
                r.started_at = now
        return rows

    def mark_completed(self, task_id: uuid.UUID) -> None:
        self._db.execute(
            update(Task).where(Task.id == task_id).values(status="completed", completed_at=datetime.now(timezone.utc))
        )
        self._db.commit()

    def mark_failed(self, task_id: uuid.UUID, error: str) -> None:
        task = self._db.get(Task, task_id)
        if not task:
            return
        task.attempts += 1
        task.last_error = error[:2000]
        if task.attempts >= task.max_attempts:
            task.status = "failed"
        else:
            task.status = "pending"
        task.completed_at = None
        self._db.commit()

    def cancel(self, task_id: uuid.UUID) -> None:
        self._db.execute(
            update(Task).where(Task.id == task_id).values(status="cancelled", completed_at=datetime.now(timezone.utc))
        )
        self._db.commit()

    def get(self, task_id: uuid.UUID) -> Task | None:
        return self._db.get(Task, task_id)

    def list_by_agent(self, agent_id: uuid.UUID, *, limit: int = 50) -> list[Task]:
        return list(
            self._db.scalars(
                select(Task).where(Task.agent_id == agent_id).order_by(Task.created_at.desc()).limit(limit)
            ).all()
        )

    def pending_count(self) -> int:
        return len(list(self._db.scalars(select(Task).where(Task.status == "pending")).all()))
