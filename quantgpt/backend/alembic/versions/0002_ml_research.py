"""ml research schema

Revision ID: 0002_ml_research
Revises: 0001_initial
Create Date: 2026-07-19
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_ml_research"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ml_feature_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.String(1024), nullable=True),
        sa.Column("features", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("target_horizon", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ml_feature_sets_name", "ml_feature_sets", ["name"], unique=True)

    op.create_table(
        "ml_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("model_type", sa.String(64), nullable=False),
        sa.Column("task", sa.String(64), nullable=False, server_default="market_forecast"),
        sa.Column("description", sa.String(1024), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ml_models_name", "ml_models", ["name"], unique=True)
    op.create_index("ix_ml_models_model_type", "ml_models", ["model_type"])

    op.create_table(
        "ml_model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ml_models.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(64), nullable=False, server_default="created"),
        sa.Column("artifact_uri", sa.String(1024), nullable=True),
        sa.Column("feature_set_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ml_feature_sets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("training_metrics", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("validation_metrics", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("hyperparameters", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("model_id", "version", name="uq_ml_model_versions_model_version"),
    )
    op.create_index("ix_ml_model_versions_model_id", "ml_model_versions", ["model_id"])
    op.create_index("ix_ml_model_versions_status", "ml_model_versions", ["status"])

    op.create_table(
        "ml_training_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ml_models.id", ondelete="SET NULL"), nullable=True),
        sa.Column("model_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ml_model_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(64), nullable=False, server_default="pending"),
        sa.Column("requested_model_type", sa.String(64), nullable=False),
        sa.Column("dataset", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("feature_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("training_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("metrics", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("error", sa.String(2048), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ml_training_runs_model_id", "ml_training_runs", ["model_id"])
    op.create_index("ix_ml_training_runs_model_version_id", "ml_training_runs", ["model_version_id"])
    op.create_index("ix_ml_training_runs_status", "ml_training_runs", ["status"])
    op.create_index("ix_ml_training_runs_requested_model_type", "ml_training_runs", ["requested_model_type"])

    op.create_table(
        "ml_inference_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("model_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ml_model_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("symbol", sa.String(128), nullable=False),
        sa.Column("exchange", sa.String(64), nullable=False),
        sa.Column("probability_up", sa.Float(), nullable=False),
        sa.Column("probability_down", sa.Float(), nullable=False),
        sa.Column("expected_return", sa.Float(), nullable=False),
        sa.Column("volatility", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ml_inference_records_symbol", "ml_inference_records", ["symbol"])
    op.create_index("ix_ml_inference_records_exchange", "ml_inference_records", ["exchange"])


def downgrade() -> None:
    op.drop_index("ix_ml_inference_records_exchange", table_name="ml_inference_records")
    op.drop_index("ix_ml_inference_records_symbol", table_name="ml_inference_records")
    op.drop_table("ml_inference_records")
    op.drop_index("ix_ml_training_runs_requested_model_type", table_name="ml_training_runs")
    op.drop_index("ix_ml_training_runs_status", table_name="ml_training_runs")
    op.drop_index("ix_ml_training_runs_model_version_id", table_name="ml_training_runs")
    op.drop_index("ix_ml_training_runs_model_id", table_name="ml_training_runs")
    op.drop_table("ml_training_runs")
    op.drop_index("ix_ml_model_versions_status", table_name="ml_model_versions")
    op.drop_index("ix_ml_model_versions_model_id", table_name="ml_model_versions")
    op.drop_table("ml_model_versions")
    op.drop_index("ix_ml_models_model_type", table_name="ml_models")
    op.drop_index("ix_ml_models_name", table_name="ml_models")
    op.drop_table("ml_models")
    op.drop_index("ix_ml_feature_sets_name", table_name="ml_feature_sets")
    op.drop_table("ml_feature_sets")
