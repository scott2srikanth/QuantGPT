"""AgentRegistry — maps agent names to their AgentBase instances.

The registry is the single source of truth for which agents exist. The
manager and scheduler look up agents by name through the registry. Agents
are registered at startup (see agents/__init__.py) and cannot be re-registered.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentBase
from app.agents.exceptions import AgentAlreadyRegisteredError, AgentNotFoundError


class AgentRegistry:
    """In-memory registry of agent name -> AgentBase instance."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentBase] = {}

    def register(self, agent: AgentBase) -> None:
        if agent.name in self._agents:
            raise AgentAlreadyRegisteredError(f"agent '{agent.name}' already registered")
        self._agents[agent.name] = agent

    def get(self, name: str) -> AgentBase:
        if name not in self._agents:
            raise AgentNotFoundError(f"agent '{name}' not registered")
        return self._agents[name]

    def all(self) -> dict[str, AgentBase]:
        return dict(self._agents)

    def names(self) -> list[str]:
        return sorted(self._agents.keys())

    def contains(self, name: str) -> bool:
        return name in self._agents

    def __len__(self) -> int:
        return len(self._agents)
