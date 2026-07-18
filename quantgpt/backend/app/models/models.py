"""ORM models for QuantGPT."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    roles: Mapped[list["Role"]] = relationship("Role", secondary="user_roles", back_populates="users")


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    users: Mapped[list["User"]] = relationship("User", secondary="user_roles", back_populates="roles")


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(default=False, nullable=False)


# ── Agent framework ──
class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="idle", index=True, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="pending", index=True, nullable=False)
    priority: Mapped[int] = mapped_column(default=0, nullable=False)
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(default=3, nullable=False)
    last_error: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    from_agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    to_agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), index=True, nullable=True)
    topic: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    delivered: Mapped[bool] = mapped_column(default=False, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentMemory(Base, TimestampMixin):
    __tablename__ = "agent_memory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (UniqueConstraint("agent_id", "key", name="uq_agent_memory_agent_key"),)


class AgentHistory(Base):
    __tablename__ = "agent_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=_uuid, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentMetric(Base):
    __tablename__ = "agent_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    metric: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    value: Mapped[Decimal] = mapped_column(nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)


class AgentHealth(Base):
    __tablename__ = "agent_health"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="healthy", nullable=False)
    detail: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)


# ── ML research ──
class MLFeatureSet(Base, TimestampMixin):
    __tablename__ = "ml_feature_sets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    features: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    target_horizon: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class MLModel(Base, TimestampMixin):
    __tablename__ = "ml_models"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    model_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    task: Mapped[str] = mapped_column(String(64), default="market_forecast", nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)


class MLModelVersion(Base, TimestampMixin):
    __tablename__ = "ml_model_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ml_models.id", ondelete="CASCADE"), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="created", index=True, nullable=False)
    artifact_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    feature_set_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ml_feature_sets.id", ondelete="SET NULL"), nullable=True)
    training_metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    validation_metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    hyperparameters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)

    __table_args__ = (UniqueConstraint("model_id", "version", name="uq_ml_model_versions_model_version"),)


class MLTrainingRun(Base, TimestampMixin):
    __tablename__ = "ml_training_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    model_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ml_models.id", ondelete="SET NULL"), nullable=True)
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ml_model_versions.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="pending", index=True, nullable=False)
    requested_model_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    dataset: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    feature_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    training_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MLInferenceRecord(Base):
    __tablename__ = "ml_inference_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ml_model_versions.id", ondelete="SET NULL"), nullable=True)
    symbol: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    probability_up: Mapped[float] = mapped_column(Float, nullable=False)
    probability_down: Mapped[float] = mapped_column(Float, nullable=False)
    expected_return: Mapped[float] = mapped_column(Float, nullable=False)
    volatility: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    inputs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ── Risk engine ──
class RiskPolicy(Base, TimestampMixin):
    __tablename__ = "risk_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    max_position_notional: Mapped[float] = mapped_column(Float, default=100000.0, nullable=False)
    max_order_notional: Mapped[float] = mapped_column(Float, default=50000.0, nullable=False)
    max_portfolio_heat: Mapped[float] = mapped_column(Float, default=0.06, nullable=False)
    max_symbol_exposure_pct: Mapped[float] = mapped_column(Float, default=0.15, nullable=False)
    max_sector_exposure_pct: Mapped[float] = mapped_column(Float, default=0.30, nullable=False)
    max_gross_exposure_pct: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    max_loss_per_trade_pct: Mapped[float] = mapped_column(Float, default=0.01, nullable=False)
    daily_stop_loss_pct: Mapped[float] = mapped_column(Float, default=0.03, nullable=False)
    weekly_stop_loss_pct: Mapped[float] = mapped_column(Float, default=0.06, nullable=False)
    monthly_stop_loss_pct: Mapped[float] = mapped_column(Float, default=0.10, nullable=False)
    max_drawdown_pct: Mapped[float] = mapped_column(Float, default=0.15, nullable=False)
    correlation_limit: Mapped[float] = mapped_column(Float, default=0.85, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)


class RiskApproval(Base):
    __tablename__ = "risk_approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    policy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("risk_policies.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_price: Mapped[float] = mapped_column(Float, nullable=False)
    notional: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    checks: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    request: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RiskLimitState(Base, TimestampMixin):
    __tablename__ = "risk_limit_state"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    scope: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    peak_equity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    current_equity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
