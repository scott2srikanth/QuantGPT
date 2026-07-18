"""AgentBase — the abstract base class every agent extends.

Every agent in QuantGPT exposes a uniform interface:
    run()      — execute the agent's task with the given payload
    status()   — current lifecycle status (idle/running/error)
    metrics()  — rolling numeric metrics (latency, throughput, etc.)
    health()   — health snapshot (healthy/degraded/unhealthy)
    config()   — the agent's configuration dict
    memory()   — the agent's persisted key/value memory
    history()  — recent execution history rows

The base class handles persistence (history, metrics, health, memory),
retry logic, and structured logging. Concrete agents only implement
`execute(payload)` and optionally `check_health()`.

Retry logic: run() retries `execute()` up to `max_attempts` (from config or
the task), with exponential backoff. Non-retryable exceptions abort
immediately. All attempts are recorded in history and metrics.
"""

from __future__ import annotations

import abc
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.agents.exceptions import TaskExecutionError, TaskMaxAttemptsExceededError
from app.agents.health import HealthTracker
from app.agents.history import HistoryStore
from app.agents.memory import Memory
from app.agents.metrics import MetricsStore
from app.logging.config import get_logger

# Exceptions that should not be retried (fail fast)
NON_RETRYABLE = (TaskMaxAttemptsExceededError,)


class AgentBase(abc.ABC):
    """Abstract base for all QuantGPT agents.

    Concrete agents set `name`, `type`, and implement `execute(payload)`.
    They may override `check_health()` to report custom health status.
    """

    name: str = ""
    type: str = "base"

    def __init__(
        self,
        *,
        agent_id: uuid.UUID,
        db: Session,
        config: dict[str, Any] | None = None,
        max_attempts: int = 3,
    ) -> None:
        self.id = agent_id
        self._db = db
        self._config = config or {}
        self._max_attempts = max_attempts
        self._log = get_logger(f"agent.{self.name}")
        self._status: str = "idle"
        self._memory = Memory(agent_id, db)
        self._history = HistoryStore(db)
        self._metrics = MetricsStore(db)
        self._health = HealthTracker(db)

    # ── lifecycle status ──
    def status(self) -> dict[str, Any]:
        return {"name": self.name, "type": self.type, "status": self._status, "running": self._status == "running"}

    # ── config ──
    def config(self) -> dict[str, Any]:
        return {"name": self.name, "type": self.type, "config": self._config}

    # ── memory ──
    def memory(self) -> dict[str, Any]:
        return self._memory.all()

    # ── history ──
    def history(self, *, limit: int = 50) -> list[Any]:
        return self._history.list_by_agent(self.id, limit=limit)

    # ── metrics ──
    def metrics(self) -> dict[str, float]:
        return self._metrics.latest(self.id)

    # ── health ──
    def health(self) -> dict[str, Any]:
        latest = self._health.latest(self.id)
        if latest:
            return {"name": self.name, "status": latest.status, "detail": latest.detail, "checked_at": latest.checked_at}
        return {"name": self.name, "status": "healthy", "detail": None, "checked_at": None}

    def _record_health(self, status: str, detail: str | None = None) -> None:
        self._health.record(self.id, status, detail)  # type: ignore[arg-type]

    def check_health(self) -> tuple[str, str | None]:
        """Override to report custom health. Returns (status, detail)."""
        return "healthy", None

    # ── run with retry ──
    def run(self, payload: dict[str, Any] | None = None, *, max_attempts: int | None = None) -> dict[str, Any]:
        attempts = max_attempts if max_attempts is not None else self._max_attempts
        run_id = uuid.uuid4()
        self._status = "running"
        self._log.info("agent.run.start", agent=self.name, run_id=str(run_id), payload=payload)

        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            start = time.monotonic()
            try:
                result = self.execute(payload or {})
                duration_ms = int((time.monotonic() - start) * 1000)
                self._history.record(
                    agent_id=self.id, run_id=run_id, status="completed", result=result, duration_ms=duration_ms
                )
                self._metrics.record(self.id, "duration_ms", float(duration_ms))
                self._metrics.record(self.id, "attempts", float(attempt))
                self._status = "idle"
                self._record_health("healthy")
                self._log.info("agent.run.complete", agent=self.name, run_id=str(run_id), duration_ms=duration_ms, attempt=attempt)
                return {"run_id": str(run_id), "status": "completed", "result": result, "duration_ms": duration_ms, "attempts": attempt}
            except NON_RETRYABLE:
                duration_ms = int((time.monotonic() - start) * 1000)
                err = TaskMaxAttemptsExceededError(f"{self.name} failed (non-retryable)", agent_name=self.name)
                self._history.record(
                    agent_id=self.id, run_id=run_id, status="failed", result={}, duration_ms=duration_ms, error=str(err)
                )
                self._metrics.record(self.id, "errors", 1.0)
                self._status = "error"
                self._record_health("unhealthy", str(err))
                self._log.error("agent.run.failed", agent=self.name, run_id=str(run_id), error=str(err))
                raise
            except Exception as e:
                last_error = e
                duration_ms = int((time.monotonic() - start) * 1000)
                self._metrics.record(self.id, "duration_ms", float(duration_ms))
                self._metrics.record(self.id, "errors", 1.0)
                self._log.warning("agent.run.attempt_failed", agent=self.name, run_id=str(run_id), attempt=attempt, error=str(e))
                if attempt < attempts:
                    # exponential backoff
                    backoff = min(2 ** (attempt - 1), 10)
                    time.sleep(backoff)
                    continue
                # exhausted retries
                self._history.record(
                    agent_id=self.id, run_id=run_id, status="failed", result={}, duration_ms=duration_ms, error=str(e)
                )
                self._status = "error"
                self._record_health("unhealthy", str(e))
                self._log.error("agent.run.exhausted", agent=self.name, run_id=str(run_id), attempts=attempt, error=str(e))
                raise TaskMaxAttemptsExceededError(
                    f"{self.name} failed after {attempt} attempts: {e}", agent_name=self.name, cause=e
                ) from e

        # should not reach here
        raise TaskExecutionError(f"{self.name} failed unexpectedly", agent_name=self.name, cause=last_error)

    # ── to be implemented by concrete agents ──
    @abc.abstractmethod
    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Perform the agent's work. Return a JSON-serializable result dict."""
        ...
