"""Metrics — rolling per-agent metric recording.

Agents record numeric metrics (latency, throughput, error rate, etc.) which
are persisted to the `agent_metrics` table. Aggregation is done on read.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.models import AgentMetric


class MetricsStore:
    """Persists and aggregates agent metrics."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def record(self, agent_id: uuid.UUID, metric: str, value: float) -> None:
        self._db.add(AgentMetric(agent_id=agent_id, metric=metric, value=Decimal(str(value)), recorded_at=datetime.now(timezone.utc)))
        self._db.commit()

    def latest(self, agent_id: uuid.UUID) -> dict[str, float]:
        """Return the most recent value per metric for an agent."""
        rows = list(
            self._db.scalars(
                select(AgentMetric).where(AgentMetric.agent_id == agent_id).order_by(AgentMetric.recorded_at.desc())
            ).all()
        )
        seen: set[str] = set()
        out: dict[str, float] = {}
        for r in rows:
            if r.metric not in seen:
                seen.add(r.metric)
                out[r.metric] = float(r.value)
        return out

    def summary(self, agent_id: uuid.UUID, *, window_minutes: int = 60) -> dict[str, dict[str, float]]:
        """Return avg/min/max/count per metric within a time window."""
        since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        rows = list(
            self._db.execute(
                select(
                    AgentMetric.metric,
                    func.avg(AgentMetric.value).label("avg"),
                    func.min(AgentMetric.value).label("min"),
                    func.max(AgentMetric.value).label("max"),
                    func.count(AgentMetric.value).label("cnt"),
                )
                .where(AgentMetric.agent_id == agent_id, AgentMetric.recorded_at >= since)
                .group_by(AgentMetric.metric)
            ).all()
        )
        return {
            r.metric: {"avg": float(r.avg), "min": float(r.min), "max": float(r.max), "count": int(r.cnt)}
            for r in rows
        }
