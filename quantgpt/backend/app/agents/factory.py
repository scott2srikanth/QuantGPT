"""Factory that builds the AgentManager + Scheduler with all agents registered.

This is the composition root for the agent framework. It creates each
agent with its DB session and config, registers them in the registry,
and returns a ready-to-use manager + scheduler pair.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.agents import ALL_AGENT_CLASSES
from app.agents.manager import AgentManager
from app.agents.registry import AgentRegistry
from app.agents.scheduler import Scheduler
from app.config.settings import Settings
from app.logging.config import get_logger
from app.models.models import Agent as AgentRow

_log = get_logger("agent.factory")


def build_agent_framework(db: Session, settings: Settings) -> tuple[AgentManager, Scheduler]:
    """Build the manager + scheduler with all placeholder agents registered."""
    registry = AgentRegistry()
    manager = AgentManager(db, registry)

    for cls in ALL_AGENT_CLASSES:
        # find or create the persisted agent row to get a stable id
        row = db.scalar(select(AgentRow).where(AgentRow.name == cls.name))
        if row is None:
            row = AgentRow(name=cls.name, type=cls.type, status="idle", config={})
            db.add(row)
            db.commit()
            db.refresh(row)
        agent = cls(
            agent_id=row.id,
            db=db,
            config=dict(row.config) if row.config else {},
            max_attempts=settings.agent_task_max_attempts,
        )
        manager.register(agent)

    scheduler = Scheduler(
        manager,
        interval_seconds=settings.agent_scheduler_interval_seconds,
        task_batch_size=10,
        message_batch_size=settings.agent_message_batch_size,
    )
    _log.info("agent_framework.built", agents=registry.names())
    return manager, scheduler
