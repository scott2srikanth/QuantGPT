"""Pydantic request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str | None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    roles: list[RoleOut] = []


class RoleAssignRequest(BaseModel):
    role_name: str


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
    timestamp: datetime


class HealthComponent(BaseModel):
    name: str
    status: str
    detail: str | None = None


class HealthDetailResponse(HealthResponse):
    components: list[HealthComponent]


class OpenAlgoStatus(BaseModel):
    base_url: str
    reachable: bool
    api_key_configured: bool
    websocket_url: str
    detail: str | None = None
