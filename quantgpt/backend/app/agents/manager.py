"""AgentManager — orchestrates agents, the task queue, and the message bus.

The manager is the operational entrypoint for the framework:
  - registers all agents at construction
  - enqueues tasks and dispatches them to agents
  - drains the task queue (run pending tasks)
  - delivers messages between agents
  - reports system-wide health

It is intentionally synchronous and blocking for now; the scheduler wraps
it with periodic polling. Concurrency (async workers) can be layered in
later without changing the manager's public surface.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.base import AgentBase
from app.agents.exceptions import AgentNotFoundError, TaskExecutionError
from app.agents.health import HealthTracker
from app.agents.message_bus import MessageBus
from app.agents.registry import AgentRegistry
from app.agents.task_queue import TaskQueue
from app.logging.config import get_logger
from app.models.models import Agent as AgentRow


class AgentManager:
    """Operational manager for the agent framework."""

    def __init__(self, db: Session, registry: AgentRegistry) -> None:
        self._db = db
        self._registry = registry
        self._queue = TaskQueue(db)
        self._bus = MessageBus(db)
        self._health = HealthTracker(db)
        self._log = get_logger("agent.manager")

    # ── registration persistence ──
    def _persist_agent_row(self, agent: AgentBase) -> AgentRow:
        row = self._db.scalar(select(AgentRow).where(AgentRow.name == agent.name))
        if row:
            row.type = agent.type
            row.config = agent.config().get("config", {})
            self._db.commit()
            return row
        row = AgentRow(name=agent.name, type=agent.type, status="idle", config=agent.config().get("config", {}))
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def register(self, agent: AgentBase) -> AgentBase:
        self._persist_agent_row(agent)
        self._registry.register(agent)
        self._log.info("agent.registered", agent=agent.name, type=agent.type)
        return agent

    def get(self, name: str) -> AgentBase:
        return self._registry.get(name)

    def all_agents(self) -> dict[str, AgentBase]:
        return self._registry.all()

    # ── task lifecycle ──
    def enqueue_task(
        self,
        agent_name: str,
        payload: dict[str, Any] | None = None,
        *,
        priority: int = 0,
        max_attempts: int = 3,
        scheduled_for: datetime | None = None,
    ) -> uuid.UUID:
        agent = self._registry.get(agent_name)
        task = self._queue.enqueue(
            agent_id=agent.id,
            payload=payload or {},
            priority=priority,
            max_attempts=max_attempts,
            scheduled_for=scheduled_for,
        )
        self._log.info("task.enqueued", agent=agent_name, task_id=str(task.id))
        return task.id

    def run_agent(self, agent_name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run an agent immediately (synchronously), bypassing the queue."""
        agent = self._registry.get(agent_name)
        return agent.run(payload)

    def drain(self, *, limit: int = 10) -> int:
        """Claim and execute up to `limit` pending tasks. Returns count executed."""
        tasks = self._queue.dequeue(limit=limit)
        executed = 0
        for task in tasks:
            agent = self._find_agent_by_id(task.agent_id)
            if agent is None:
                self._queue.mark_failed(task.id, "agent not found for task")
                continue
            try:
                result = agent.run(task.payload, max_attempts=task.max_attempts)
                self._queue.mark_completed(task.id)
                executed += 1
            except TaskExecutionError as e:
                self._queue.mark_failed(task.id, str(e))
                self._log.warning("task.failed", task_id=str(task.id), agent=agent.name, error=str(e))
        return executed

    def _find_agent_by_id(self, agent_id: uuid.UUID) -> AgentBase | None:
        for a in self._registry.all().values():
            if a.id == agent_id:
                return a
        return None

    # ── messaging ──
    def send_message(
        self,
        *,
        from_agent_name: str | None,
        to_agent_name: str,
        topic: str,
        payload: dict[str, Any] | None = None,
    ) -> uuid.UUID:
        from_id = self._registry.get(from_agent_name).id if from_agent_name else None
        to_id = self._registry.get(to_agent_name).id
        return self._bus.publish(from_agent_id=from_id, to_agent_id=to_id, topic=topic, payload=payload or {})

    def deliver_messages(self, *, limit: int = 50) -> int:
        """Deliver pending messages to all agents. Returns total delivered."""
        total = 0
        for agent in self._registry.all().values():
            msgs = self._bus.consume(agent.id, limit=limit)
            for m in msgs:
                # store in agent memory under the topic for later retrieval
                agent._memory.set(f"message:{m.topic}:{m.id}", {"from": str(m.from_agent_id) if m.from_agent_id else None, "payload": m.payload, "received_at": datetime.now(timezone.utc).isoformat()})
                total += 1
        return total

    # ── system health ──
    def system_health(self) -> dict[str, Any]:
        agents = self._registry.all()
        healthy = 0
        degraded = 0
        unhealthy = 0
        for a in agents.values():
            h = a.health()
            if h["status"] == "healthy":
                healthy += 1
            elif h["status"] == "degraded":
                degraded += 1
            else:
                unhealthy += 1
        return {
            "total_agents": len(agents),
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy": unhealthy,
            "pending_tasks": self._queue.pending_count(),
            "pending_messages": self._bus.pending_count(),
        }

    # ── aggregate views ──
    def all_status(self) -> list[dict[str, Any]]:
        return [a.status() for a in self._registry.all().values()]

    def all_health(self) -> list[dict[str, Any]]:
        return [a.health() for a in self._registry.all().values()]

    def all_metrics(self) -> dict[str, dict[str, float]]:
        return {name: a.metrics() for name, a in self._registry.all().items()}
