"""operational foundation

Revision ID: 0004_operational_foundation
Revises: 0003_risk_engine
Create Date: 2026-07-19
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_operational_foundation"
down_revision: Union[str, None] = "0003_risk_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column("action", sa.String(512), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("ip_hash", sa.String(64), nullable=False),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # The application already used these agent ORM models; production migrations must own them.
    op.create_table("agents", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("name", sa.String(255), nullable=False, unique=True), sa.Column("type", sa.String(128), nullable=False), sa.Column("status", sa.String(64), nullable=False, server_default="idle"), sa.Column("config", sa.JSON(), nullable=False, server_default="{}"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_agents_name", "agents", ["name"], unique=True)
    op.create_index("ix_agents_type", "agents", ["type"])
    op.create_index("ix_agents_status", "agents", ["status"])
    op.create_table("tasks", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False), sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"), sa.Column("status", sa.String(64), nullable=False, server_default="pending"), sa.Column("priority", sa.Integer(), nullable=False, server_default="0"), sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"), sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"), sa.Column("last_error", sa.String(2048)), sa.Column("scheduled_for", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_tasks_agent_id", "tasks", ["agent_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_scheduled_for", "tasks", ["scheduled_for"])
    op.create_table("messages", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("from_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="SET NULL")), sa.Column("to_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="SET NULL")), sa.Column("topic", sa.String(255), nullable=False), sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"), sa.Column("delivered", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("delivered_at", sa.DateTime(timezone=True)))
    op.create_index("ix_messages_to_agent_id", "messages", ["to_agent_id"])
    op.create_index("ix_messages_topic", "messages", ["topic"])
    op.create_index("ix_messages_delivered", "messages", ["delivered"])
    op.create_table("agent_memory", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False), sa.Column("key", sa.String(255), nullable=False), sa.Column("value", sa.JSON(), nullable=False, server_default="{}"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("agent_id", "key", name="uq_agent_memory_agent_key"))
    op.create_index("ix_agent_memory_agent_id", "agent_memory", ["agent_id"])
    op.create_table("agent_history", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False), sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("status", sa.String(64), nullable=False), sa.Column("result", sa.JSON(), nullable=False, server_default="{}"), sa.Column("duration_ms", sa.Integer()), sa.Column("error", sa.String(2048)), sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_agent_history_agent_id", "agent_history", ["agent_id"])
    op.create_index("ix_agent_history_run_id", "agent_history", ["run_id"])
    op.create_index("ix_agent_history_started_at", "agent_history", ["started_at"])
    op.create_table("agent_metrics", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False), sa.Column("metric", sa.String(255), nullable=False), sa.Column("value", sa.Numeric(), nullable=False), sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_agent_metrics_agent_id", "agent_metrics", ["agent_id"])
    op.create_index("ix_agent_metrics_metric", "agent_metrics", ["metric"])
    op.create_index("ix_agent_metrics_recorded_at", "agent_metrics", ["recorded_at"])
    op.create_table("agent_health", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False), sa.Column("status", sa.String(64), nullable=False, server_default="healthy"), sa.Column("detail", sa.String(2048)), sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_agent_health_agent_id", "agent_health", ["agent_id"])
    op.create_index("ix_agent_health_checked_at", "agent_health", ["checked_at"])


def downgrade() -> None:
    op.drop_table("agent_health")
    op.drop_table("agent_metrics")
    op.drop_table("agent_history")
    op.drop_table("agent_memory")
    op.drop_table("messages")
    op.drop_table("tasks")
    op.drop_table("agents")
    op.drop_table("audit_logs")
