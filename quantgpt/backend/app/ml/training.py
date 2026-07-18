"""Training pipeline for probabilistic ML research models."""

from __future__ import annotations

import importlib.util
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config.settings import get_settings
from sqlalchemy.orm import Session

from app.integration.models import Candle
from app.ml.feature_store import build_feature_matrix, get_or_create_feature_set
from app.ml.registry import create_version, get_or_create_model
from app.ml.schemas import MLModelType, ModelCapabilityOut, TrainingRequest
from app.models.models import MLTrainingRun


CAPABILITIES = {
    MLModelType.XGBOOST: ("xgboost", "xgboost", "XGBoost gradient boosted trees"),
    MLModelType.LIGHTGBM: ("lightgbm", "lightgbm", "LightGBM gradient boosted trees"),
    MLModelType.RANDOM_FOREST: ("sklearn", "scikit-learn", "RandomForestRegressor/Classifier"),
    MLModelType.LSTM: ("torch", "torch", "PyTorch sequence model scaffold"),
    MLModelType.TRANSFORMER: ("torch", "torch", "PyTorch transformer scaffold"),
    MLModelType.TEMPORAL_FUSION_TRANSFORMER: ("pytorch_forecasting", "pytorch-forecasting", "Temporal Fusion Transformer scaffold"),
}


def capabilities() -> list[ModelCapabilityOut]:
    out: list[ModelCapabilityOut] = []
    for model_type, (module, dependency, notes) in CAPABILITIES.items():
        out.append(
            ModelCapabilityOut(
                model_type=model_type,
                framework=module,
                dependency=dependency,
                available=importlib.util.find_spec(module) is not None,
                notes=notes,
            )
        )
    return out


def train_model(db: Session, req: TrainingRequest, candles: list[Candle]) -> MLTrainingRun:
    run = MLTrainingRun(
        status="running",
        requested_model_type=req.model_type.value,
        dataset=req.dataset.model_dump(exclude={"candles"}, mode="json"),
        feature_config=req.feature_config,
        training_config=req.training_config,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        module, dependency, notes = CAPABILITIES[req.model_type]
        if importlib.util.find_spec(module) is None:
            raise RuntimeError(
                f"{dependency} is not installed in this runtime. Install the ML dependency "
                f"and rerun training for {req.model_type.value}."
            )

        horizon = int(req.feature_config.get("target_horizon", 1))
        feature_names = req.feature_config.get("features")
        matrix = build_feature_matrix(candles, feature_names=feature_names, horizon=horizon)
        if len(matrix.rows) < 30:
            raise RuntimeError("Not enough candles to train a research model; need at least 50 usable rows.")

        feature_set = get_or_create_feature_set(
            db,
            name=req.feature_set_name or f"{req.model_name}_features",
            features=matrix.feature_names,
            target_horizon=horizon,
            config=req.feature_config,
        )
        model = get_or_create_model(
            db,
            name=req.model_name,
            model_type=req.model_type.value,
            description=req.description,
            metadata={"certainty_policy": "never_claim_certainty", "framework": module},
        )

        fitted = _fit_artifact(req.model_type, matrix.rows, matrix.targets, req.training_config)
        metrics = _research_metrics(matrix.rows, matrix.targets) | fitted["metrics"]
        version = create_version(
            db,
            model=model,
            status="trained",
            artifact_uri=fitted["artifact_uri"],
            feature_set_id=feature_set.id,
            training_metrics=metrics,
            validation_metrics={"note": "validation split hook ready; no certainty claimed"},
            hyperparameters=req.training_config,
            metadata={
                "model_family": req.model_type.value,
                "framework": module,
                "dependency": dependency,
                "notes": notes,
                "feature_names": matrix.feature_names,
                "target_horizon": horizon,
                "artifact_kind": fitted["artifact_kind"],
                "outputs": ["probability_up", "probability_down", "expected_return", "volatility", "confidence_score"],
                "certainty_policy": "probabilistic_research_only",
            },
        )
        run.model_id = model.id
        run.model_version_id = version.id
        run.status = "completed"
        run.metrics = metrics
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        run.metrics = {"certainty_policy": "no certainty claimed", "failure_type": exc.__class__.__name__}
    finally:
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
    return run


def _research_metrics(rows: list[dict[str, float]], targets: list[dict[str, float]]) -> dict[str, Any]:
    up_rate = sum(t["up"] for t in targets) / len(targets)
    avg_return = sum(t["expected_return"] for t in targets) / len(targets)
    avg_vol = sum(t["volatility"] for t in targets) / len(targets)
    return {
        "rows": len(rows),
        "feature_count": len(rows[0]) if rows else 0,
        "base_up_rate": up_rate,
        "base_down_rate": 1.0 - up_rate,
        "mean_forward_return": avg_return,
        "mean_realized_volatility": avg_vol,
        "confidence_note": "Training metrics are descriptive; forecasts remain probabilistic.",
    }


def _fit_artifact(
    model_type: MLModelType,
    rows: list[dict[str, float]],
    targets: list[dict[str, float]],
    training_config: dict[str, Any],
) -> dict[str, Any]:
    if model_type in {MLModelType.LSTM, MLModelType.TRANSFORMER, MLModelType.TEMPORAL_FUSION_TRANSFORMER}:
        return _fit_sequence_scaffold(model_type, rows, targets, training_config)

    feature_names = list(rows[0])
    x = [[row[name] for name in feature_names] for row in rows]
    y_up = [target["up"] for target in targets]
    y_return = [target["expected_return"] for target in targets]
    y_vol = [target["volatility"] for target in targets]

    if model_type == MLModelType.RANDOM_FOREST:
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

        classifier = RandomForestClassifier(
            n_estimators=int(training_config.get("n_estimators", 100)),
            random_state=int(training_config.get("random_state", 42)),
        )
        return_model = RandomForestRegressor(
            n_estimators=int(training_config.get("n_estimators", 100)),
            random_state=int(training_config.get("random_state", 42)),
        )
        vol_model = RandomForestRegressor(
            n_estimators=int(training_config.get("n_estimators", 100)),
            random_state=int(training_config.get("random_state", 42)),
        )
    elif model_type == MLModelType.XGBOOST:
        from xgboost import XGBClassifier, XGBRegressor

        classifier = XGBClassifier(
            n_estimators=int(training_config.get("n_estimators", 100)),
            max_depth=int(training_config.get("max_depth", 4)),
            learning_rate=float(training_config.get("learning_rate", 0.05)),
            eval_metric="logloss",
        )
        return_model = XGBRegressor(n_estimators=int(training_config.get("n_estimators", 100)))
        vol_model = XGBRegressor(n_estimators=int(training_config.get("n_estimators", 100)))
    elif model_type == MLModelType.LIGHTGBM:
        from lightgbm import LGBMClassifier, LGBMRegressor

        classifier = LGBMClassifier(n_estimators=int(training_config.get("n_estimators", 100)))
        return_model = LGBMRegressor(n_estimators=int(training_config.get("n_estimators", 100)))
        vol_model = LGBMRegressor(n_estimators=int(training_config.get("n_estimators", 100)))
    else:
        raise RuntimeError(f"Unsupported model type: {model_type.value}")

    classifier.fit(x, y_up)
    return_model.fit(x, y_return)
    vol_model.fit(x, y_vol)
    artifact = {
        "model_type": model_type.value,
        "artifact_kind": "pickled_tabular_ensemble",
        "feature_names": feature_names,
        "classifier": classifier,
        "return_model": return_model,
        "volatility_model": vol_model,
        "certainty_policy": "no certainty claimed",
    }
    artifact_uri = _write_artifact(model_type.value, artifact)
    predictions = classifier.predict(x)
    accuracy = sum(1 for pred, actual in zip(predictions, y_up, strict=False) if float(pred) == actual) / len(y_up)
    return {
        "artifact_uri": artifact_uri,
        "artifact_kind": "pickled_tabular_ensemble",
        "metrics": {"in_sample_direction_accuracy": accuracy},
    }


def _fit_sequence_scaffold(
    model_type: MLModelType,
    rows: list[dict[str, float]],
    targets: list[dict[str, float]],
    training_config: dict[str, Any],
) -> dict[str, Any]:
    import torch

    artifact = {
        "model_type": model_type.value,
        "framework": "torch",
        "feature_names": list(rows[0]),
        "sample_count": len(rows),
        "target_summary": _research_metrics(rows, targets),
        "training_config": training_config,
        "note": (
            "Sequence model scaffold recorded. Full LSTM/Transformer/TFT training requires "
            "windowed tensor datasets and accelerator-aware training, but predictions remain probabilistic."
        ),
        "torch_version": torch.__version__,
        "certainty_policy": "no certainty claimed",
    }
    artifact_uri = _write_artifact(model_type.value, artifact)
    return {
        "artifact_uri": artifact_uri,
        "artifact_kind": "sequence_model_scaffold",
        "metrics": {"sequence_training_status": "scaffold_recorded", "sample_count": len(rows)},
    }


def _write_artifact(model_type: str, artifact: dict[str, Any]) -> str:
    base = Path(get_settings().ml_model_artifact_dir)
    base.mkdir(parents=True, exist_ok=True)
    filename = f"{model_type}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}.pkl"
    path = base / filename
    with path.open("wb") as fh:
        pickle.dump(artifact, fh)
    return str(path)
