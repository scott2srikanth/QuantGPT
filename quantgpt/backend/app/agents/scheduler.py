"""Scheduler — periodically drains the task queue and delivers messages.

The scheduler runs in a background thread and ticks at a configurable
interval. Each tick:
  1. Delivers pending messages to agents
  2. Drains up to N pending tasks from the queue and executes them

It is stoppable and idempotent. Concurrency (async workers, parallel task
execution) can be layered in later without changing the scheduler's surface.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from app.agents.manager import AgentManager
from app.logging.config import get_logger


class Scheduler:
    """Background scheduler for the agent framework."""

    def __init__(
        self,
        manager: AgentManager,
        *,
        interval_seconds: float = 5.0,
        task_batch_size: int = 10,
        message_batch_size: int = 50,
    ) -> None:
        self._manager = manager
        self._interval = interval_seconds
        self._task_batch = task_batch_size
        self._message_batch = message_batch_size
        self._log = get_logger("agent.scheduler")
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="agent-scheduler", daemon=True)
        self._thread.start()
        self._running = True
        self._log.info("scheduler.started", interval=self._interval)

    def stop(self, *, timeout: float = 5.0) -> None:
        if not self._running:
            return
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        self._running = False
        self._log.info("scheduler.stopped")

    def is_running(self) -> bool:
        return self._running

    def tick(self) -> dict[str, Any]:
        """Run one scheduler iteration. Exposed for testing and manual triggers."""
        delivered = self._manager.deliver_messages(limit=self._message_batch)
        executed = self._manager.drain(limit=self._task_batch)
        self._log.debug("scheduler.tick", delivered=delivered, executed=executed)
        return {"delivered_messages": delivered, "executed_tasks": executed}

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:
                self._log.exception("scheduler.tick.error")
            self._stop.wait(self._interval)
