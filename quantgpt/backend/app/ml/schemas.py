"""Schemas for ML research workflows."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.integration.models import Candle


class MLModelType(str, Enum):
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    RANDOM_FOREST = "random_forest"
    LSTM = "lstm"
    TRANSFORMER = "transformer"
    TEMPORAL_FUSION_TRANSFORMER = "temporal_fusion_transformer"


class FeatureSetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1024)
    features: list[str] = Field(default_factory=list)
    target_horizon: int = Field(default=1, ge=1, le=252)
    config: dict[str, Any] = Field(default_factory=dict)


class FeatureSetOut(FeatureSetCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class TrainingDatasetRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"
    interval: str = "D"
    limit: int = Field(default=500, ge=50, le=5000)
    candles: list[Candle] | None = None


class TrainingRequest(BaseModel):
    model_name: str = Field(min_length=1, max_length=255)
    model_type: MLModelType
    description: str | None = Field(default=None, max_length=1024)
    dataset: TrainingDatasetRequest
    feature_set_name: str | None = None
    feature_config: dict[str, Any] = Field(default_factory=dict)
    training_config: dict[str, Any] = Field(default_factory=dict)
    retrain_from_model_id: uuid.UUID | None = None


class TrainingRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    model_id: uuid.UUID | None
    model_version_id: uuid.UUID | None
    status: str
    requested_model_type: str
    dataset: dict[str, Any]
    feature_config: dict[str, Any]
    training_config: dict[str, Any]
    metrics: dict[str, Any]
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    model_type: str
    task: str
    description: str | None
    metadata_: dict[str, Any] = Field(validation_alias="metadata_", serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime


class ModelVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    model_id: uuid.UUID
    version: int
    status: str
    artifact_uri: str | None
    feature_set_id: uuid.UUID | None
    training_metrics: dict[str, Any]
    validation_metrics: dict[str, Any]
    hyperparameters: dict[str, Any]
    metadata_: dict[str, Any] = Field(validation_alias="metadata_", serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime


class InferenceRequest(BaseModel):
    model_version_id: uuid.UUID | None = None
    symbol: str
    exchange: str = "NSE"
    interval: str = "D"
    limit: int = Field(default=200, ge=30, le=5000)
    candles: list[Candle] | None = None
    features: dict[str, float] | None = None


class ForecastOut(BaseModel):
    symbol: str
    exchange: str
    model_version_id: uuid.UUID | None
    probability_up: float = Field(ge=0, le=1)
    probability_down: float = Field(ge=0, le=1)
    expected_return: float
    volatility: float = Field(ge=0)
    confidence_score: float = Field(ge=0, le=1)
    horizon: int
    certainty_claim: str = "No certainty claimed; this is a probabilistic research forecast."
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("probability_down")
    @classmethod
    def _probabilities_are_bounded(cls, value: float) -> float:
        return min(max(value, 0.0), 1.0)


class ModelCapabilityOut(BaseModel):
    model_type: MLModelType
    framework: str
    available: bool
    dependency: str
    notes: str
