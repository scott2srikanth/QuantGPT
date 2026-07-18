"""ML research API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.auth import roles as rc
from app.core.container import get_container
from app.db.session import get_db
from app.ml.feature_store import DEFAULT_FEATURES
from app.ml.inference import infer_forecast
from app.ml.schemas import (
    FeatureSetCreate,
    FeatureSetOut,
    ForecastOut,
    InferenceRequest,
    ModelCapabilityOut,
    ModelOut,
    ModelVersionOut,
    TrainingRequest,
    TrainingRunOut,
)
from app.ml.training import capabilities, train_model
from app.models.models import MLFeatureSet, MLModel, MLModelVersion, MLTrainingRun, User

router = APIRouter(prefix="/ml", tags=["ml-research"])


@router.get("/capabilities", response_model=list[ModelCapabilityOut])
def get_capabilities(_: User = Depends(require_roles(rc.ADMIN, rc.TRADER, rc.VIEWER))):
    return capabilities()


@router.post("/feature-sets", response_model=FeatureSetOut)
def create_feature_set(
    payload: FeatureSetCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(rc.ADMIN, rc.TRADER)),
):
    row = MLFeatureSet(
        name=payload.name,
        description=payload.description,
        features=payload.features or DEFAULT_FEATURES,
        target_horizon=payload.target_horizon,
        config=payload.config,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/feature-sets", response_model=list[FeatureSetOut])
def list_feature_sets(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(rc.ADMIN, rc.TRADER, rc.VIEWER)),
):
    return db.scalars(select(MLFeatureSet).order_by(MLFeatureSet.created_at.desc())).all()


@router.post("/train", response_model=TrainingRunOut)
def train(
    payload: TrainingRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(rc.ADMIN, rc.TRADER)),
):
    candles = payload.dataset.candles
    if candles is None:
        try:
            candles = get_container().integration.history(
                payload.dataset.symbol,
                payload.dataset.exchange,
                payload.dataset.interval,
                limit=payload.dataset.limit,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch training candles: {exc}") from exc
    return train_model(db, payload, candles)


@router.get("/training-runs", response_model=list[TrainingRunOut])
def list_training_runs(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(rc.ADMIN, rc.TRADER, rc.VIEWER)),
):
    return db.scalars(select(MLTrainingRun).order_by(MLTrainingRun.created_at.desc()).limit(100)).all()


@router.get("/models", response_model=list[ModelOut])
def list_models(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(rc.ADMIN, rc.TRADER, rc.VIEWER)),
):
    return db.scalars(select(MLModel).order_by(MLModel.created_at.desc())).all()


@router.get("/models/{model_id}/versions", response_model=list[ModelVersionOut])
def list_model_versions(
    model_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(rc.ADMIN, rc.TRADER, rc.VIEWER)),
):
    return db.scalars(
        select(MLModelVersion)
        .where(MLModelVersion.model_id == model_id)
        .order_by(MLModelVersion.version.desc())
    ).all()


@router.post("/infer", response_model=ForecastOut)
def infer(
    payload: InferenceRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(rc.ADMIN, rc.TRADER, rc.VIEWER)),
):
    candles = payload.candles
    if candles is None and payload.features is None:
        try:
            candles = get_container().integration.history(
                payload.symbol,
                payload.exchange,
                payload.interval,
                limit=payload.limit,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch inference candles: {exc}") from exc
    return infer_forecast(
        db,
        symbol=payload.symbol,
        exchange=payload.exchange,
        candles=candles or [],
        model_version_id=payload.model_version_id,
        explicit_features=payload.features,
    )
