"""Model registry and versioning helpers."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.models import MLModel, MLModelVersion


def get_or_create_model(
    db: Session,
    *,
    name: str,
    model_type: str,
    description: str | None = None,
    metadata: dict | None = None,
) -> MLModel:
    row = db.scalar(select(MLModel).where(MLModel.name == name))
    if row:
        return row
    row = MLModel(
        name=name,
        model_type=model_type,
        description=description,
        metadata_=metadata or {},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def next_version(db: Session, model_id: uuid.UUID) -> int:
    current = db.scalar(select(func.max(MLModelVersion.version)).where(MLModelVersion.model_id == model_id))
    return int(current or 0) + 1


def create_version(
    db: Session,
    *,
    model: MLModel,
    status: str,
    artifact_uri: str | None,
    feature_set_id: uuid.UUID | None,
    training_metrics: dict,
    validation_metrics: dict,
    hyperparameters: dict,
    metadata: dict,
) -> MLModelVersion:
    row = MLModelVersion(
        model_id=model.id,
        version=next_version(db, model.id),
        status=status,
        artifact_uri=artifact_uri,
        feature_set_id=feature_set_id,
        training_metrics=training_metrics,
        validation_metrics=validation_metrics,
        hyperparameters=hyperparameters,
        metadata_=metadata,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
