"""risk engine schema

Revision ID: 0003_risk_engine
Revises: 0002_ml_research
Create Date: 2026-07-19
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_risk_engine"
down_revision: Union[str, None] = "0002_ml_research"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "risk_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("max_position_notional", sa.Float(), nullable=False, server_default="100000"),
        sa.Column("max_order_notional", sa.Float(), nullable=False, server_default="50000"),
        sa.Column("max_portfolio_heat", sa.Float(), nullable=False, server_default="0.06"),
        sa.Column("max_symbol_exposure_pct", sa.Float(), nullable=False, server_default="0.15"),
        sa.Column("max_sector_exposure_pct", sa.Float(), nullable=False, server_default="0.30"),
        sa.Column("max_gross_exposure_pct", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("max_loss_per_trade_pct", sa.Float(), nullable=False, server_default="0.01"),
        sa.Column("daily_stop_loss_pct", sa.Float(), nullable=False, server_default="0.03"),
        sa.Column("weekly_stop_loss_pct", sa.Float(), nullable=False, server_default="0.06"),
        sa.Column("monthly_stop_loss_pct", sa.Float(), nullable=False, server_default="0.10"),
        sa.Column("max_drawdown_pct", sa.Float(), nullable=False, server_default="0.15"),
        sa.Column("correlation_limit", sa.Float(), nullable=False, server_default="0.85"),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_risk_policies_name", "risk_policies", ["name"], unique=True)
    op.create_index("ix_risk_policies_is_active", "risk_policies", ["is_active"])

    op.create_table(
        "risk_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("risk_policies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(128), nullable=False),
        sa.Column("exchange", sa.String(64), nullable=False),
        sa.Column("side", sa.String(16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("estimated_price", sa.Float(), nullable=False),
        sa.Column("notional", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("checks", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("request", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_risk_approvals_status", "risk_approvals", ["status"])
    op.create_index("ix_risk_approvals_symbol", "risk_approvals", ["symbol"])
    op.create_index("ix_risk_approvals_exchange", "risk_approvals", ["exchange"])

    op.create_table(
        "risk_limit_state",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scope", sa.String(64), nullable=False, unique=True),
        sa.Column("realized_pnl", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unrealized_pnl", sa.Float(), nullable=False, server_default="0"),
        sa.Column("peak_equity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("current_equity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_risk_limit_state_scope", "risk_limit_state", ["scope"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_risk_limit_state_scope", table_name="risk_limit_state")
    op.drop_table("risk_limit_state")
    op.drop_index("ix_risk_approvals_exchange", table_name="risk_approvals")
    op.drop_index("ix_risk_approvals_symbol", table_name="risk_approvals")
    op.drop_index("ix_risk_approvals_status", table_name="risk_approvals")
    op.drop_table("risk_approvals")
    op.drop_index("ix_risk_policies_is_active", table_name="risk_policies")
    op.drop_index("ix_risk_policies_name", table_name="risk_policies")
    op.drop_table("risk_policies")
