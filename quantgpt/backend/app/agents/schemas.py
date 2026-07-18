"""Pydantic schemas for the agent framework API surface."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    type: str
    status: str
    running: bool


class AgentConfig(BaseModel):
    name: str
    type: str
    config: dict[str, Any] = Field(default_factory=dict)


class AgentHealthOut(BaseModel):
    name: str
    status: str
    detail: str | None = None
    checked_at: datetime | None = None


class AgentMetricsOut(BaseModel):
    name: str
    metrics: dict[str, float] = Field(default_factory=dict)


class AgentMemoryOut(BaseModel):
    name: str
    memory: dict[str, Any] = Field(default_factory=dict)


class AgentHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    run_id: uuid.UUID
    status: str
    result: dict[str, Any]
    duration_ms: int | None
    error: str | None
    started_at: datetime
    completed_at: datetime | None


class TaskCreate(BaseModel):
    agent_name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = 0
    max_attempts: int = 3
    scheduled_for: datetime | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    agent_id: uuid.UUID
    agent_name: str | None = None
    payload: dict[str, Any]
    status: str
    priority: int
    attempts: int
    max_attempts: int
    last_error: str | None
    created_at: datetime


class MessageCreate(BaseModel):
    from_agent_name: str | None = None
    to_agent_name: str
    topic: str
    payload: dict[str, Any] = Field(default_factory=dict)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    from_agent_name: str | None
    to_agent_name: str | None
    topic: str
    payload: dict[str, Any]
    delivered: bool
    created_at: datetime
    delivered_at: datetime | None


class AgentRunRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
