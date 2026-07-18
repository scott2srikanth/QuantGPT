"""Application DI container. Wires the Integration Layer facade + agent framework."""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.manager import AgentManager
from app.agents.scheduler import Scheduler
from app.config.settings import Settings, get_settings
from app.db.session import SessionLocal
from app.integration.facade import IntegrationFacade


@dataclass
class Container:
    settings: Settings
    integration: IntegrationFacade
    agent_manager: AgentManager
    scheduler: Scheduler


_container: Container | None = None


def build_container() -> Container:
    s = get_settings()
    integration = IntegrationFacade.from_settings(s)

    # Build the agent framework with its own DB session
    from app.agents.factory import build_agent_framework

    db = SessionLocal()
    agent_manager, scheduler = build_agent_framework(db, s)

    return Container(
        settings=s,
        integration=integration,
        agent_manager=agent_manager,
        scheduler=scheduler,
    )


def get_container() -> Container:
    global _container
    if _container is None:
        _container = build_container()
    return _container


def get_agent_manager(db=None):
    """Return an AgentManager bound to the given DB session (per-request)."""
    from app.agents.factory import build_agent_framework
    from app.config.settings import get_settings

    s = get_settings()
    manager, _ = build_agent_framework(db, s)
    return manager
