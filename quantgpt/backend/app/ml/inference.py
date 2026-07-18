"""Inference engine for probabilistic research forecasts."""

from __future__ import annotations

import math
import pickle
import uuid
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from sqlalchemy.orm import Session

from app.integration.models import Candle
from app.ml.feature_store import latest_feature_row
from app.models.models import MLInferenceRecord, MLModelVersion


def infer_forecast(
    db: Session,
    *,
    symbol: str,
    exchange: str,
    candles: list[Candle],
    model_version_id: uuid.UUID | None = None,
    explicit_features: dict[str, float] | None = None,
) -> dict[str, Any]:
    version = db.get(MLModelVersion, model_version_id) if model_version_id else None
    features = explicit_features or latest_feature_row(candles)
    returns = _returns(candles)
    expected_return = mean(returns[-20:]) if returns else 0.0
    volatility = pstdev(returns[-20:]) if len(returns) > 1 else abs(features.get("volatility_20", 0.0))

    artifact_prediction = _predict_from_artifact(version, features)
    if artifact_prediction:
        probability_up = artifact_prediction["probability_up"]
        probability_down = 1.0 - probability_up
        expected_return = artifact_prediction.get("expected_return", expected_return)
        volatility = max(0.0, artifact_prediction.get("volatility", volatility))
        engine = artifact_prediction["engine"]
    else:
        momentum = features.get("return_5", 0.0) + features.get("sma_gap_10", 0.0)
        probability_up = _bounded_probability(_sigmoid(momentum / max(volatility, 0.0001)))
        probability_down = 1.0 - probability_up
        engine = "feature_baseline"
    confidence = _confidence(probability_up, len(candles), version)

    record = MLInferenceRecord(
        model_version_id=version.id if version else None,
        symbol=symbol,
        exchange=exchange,
        probability_up=probability_up,
        probability_down=probability_down,
        expected_return=expected_return,
        volatility=volatility,
        confidence_score=confidence,
        inputs={"features": features, "candle_count": len(candles)},
        metadata_={
            "certainty_policy": "no certainty claimed",
            "engine": engine,
            "model_status": version.status if version else "unversioned_feature_baseline",
        },
    )
    db.add(record)
    db.commit()

    return {
        "symbol": symbol,
        "exchange": exchange,
        "model_version_id": version.id if version else None,
        "probability_up": probability_up,
        "probability_down": probability_down,
        "expected_return": expected_return,
        "volatility": volatility,
        "confidence_score": confidence,
        "horizon": _horizon(version),
        "metadata": record.metadata_,
    }


def _returns(candles: list[Candle]) -> list[float]:
    closes = [float(c.close) for c in candles]
    return [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1]]


def _predict_from_artifact(version: MLModelVersion | None, features: dict[str, float]) -> dict[str, float | str] | None:
    if not version or not version.artifact_uri:
        return None
    path = Path(version.artifact_uri)
    if not path.exists():
        return None
    with path.open("rb") as fh:
        artifact = pickle.load(fh)
    if artifact.get("artifact_kind") == "sequence_model_scaffold":
        return None
    feature_names = artifact.get("feature_names", [])
    row = [[features.get(name, 0.0) for name in feature_names]]
    classifier = artifact.get("classifier")
    return_model = artifact.get("return_model")
    volatility_model = artifact.get("volatility_model")
    if classifier is None:
        return None
    if hasattr(classifier, "predict_proba"):
        probability_up = float(classifier.predict_proba(row)[0][-1])
    else:
        probability_up = float(classifier.predict(row)[0])
    expected_return = float(return_model.predict(row)[0]) if return_model is not None else 0.0
    volatility = abs(float(volatility_model.predict(row)[0])) if volatility_model is not None else 0.0
    return {
        "probability_up": _bounded_probability(probability_up),
        "expected_return": expected_return,
        "volatility": volatility,
        "engine": "versioned_model_artifact",
    }


def _sigmoid(value: float) -> float:
    value = max(min(value, 20.0), -20.0)
    return 1.0 / (1.0 + math.exp(-value))


def _bounded_probability(value: float) -> float:
    return max(0.001, min(0.999, value))


def _confidence(probability_up: float, sample_size: int, version: MLModelVersion | None) -> float:
    probability_edge = abs(probability_up - 0.5) * 2
    sample_factor = min(sample_size / 500, 1.0)
    version_factor = 1.0 if version and version.status == "trained" else 0.45
    return max(0.0, min(1.0, probability_edge * 0.6 + sample_factor * 0.25 + version_factor * 0.15))


def _horizon(version: MLModelVersion | None) -> int:
    if not version:
        return 1
    return int(version.metadata_.get("target_horizon", 1))
