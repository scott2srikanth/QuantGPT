"""Agent framework exceptions."""

from __future__ import annotations


class AgentError(Exception):
    """Base error for the agent framework."""


class AgentNotFoundError(AgentError):
    """Requested agent is not registered."""


class AgentAlreadyRegisteredError(AgentError):
    """An agent with this name is already registered."""


class TaskNotFoundError(AgentError):
    """Requested task does not exist."""


class TaskExecutionError(AgentError):
    """An agent failed to execute a task."""

    def __init__(self, message: str, *, agent_name: str | None = None, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.agent_name = agent_name
        self.cause = cause


class TaskMaxAttemptsExceededError(TaskExecutionError):
    """A task exceeded its retry budget."""


class SchedulerError(AgentError):
    """Scheduler encountered an error."""


class MessageDeliveryError(AgentError):
    """A message could not be delivered."""
