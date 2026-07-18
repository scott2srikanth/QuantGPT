"""Feature store primitives for ML research."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean, pstdev

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integration.models import Candle
from app.models.models import MLFeatureSet


DEFAULT_FEATURES = [
    "return_1",
    "return_3",
    "return_5",
    "return_10",
    "volatility_10",
    "volatility_20",
    "range_pct",
    "volume_change",
    "sma_gap_10",
    "sma_gap_20",
]


@dataclass(frozen=True)
class FeatureMatrix:
    feature_names: list[str]
    rows: list[dict[str, float]]
    targets: list[dict[str, float]]
    horizon: int


def get_or_create_feature_set(
    db: Session,
    *,
    name: str,
    features: list[str] | None = None,
    target_horizon: int = 1,
    config: dict | None = None,
) -> MLFeatureSet:
    row = db.scalar(select(MLFeatureSet).where(MLFeatureSet.name == name))
    if row:
        return row
    row = MLFeatureSet(
        name=name,
        features=features or DEFAULT_FEATURES,
        target_horizon=target_horizon,
        config=config or {},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def latest_feature_row(candles: list[Candle], feature_names: list[str] | None = None) -> dict[str, float]:
    matrix = build_feature_matrix(candles, feature_names=feature_names, horizon=1, include_targets=False)
    return matrix.rows[-1] if matrix.rows else {}


def build_feature_matrix(
    candles: list[Candle],
    *,
    feature_names: list[str] | None = None,
    horizon: int = 1,
    include_targets: bool = True,
) -> FeatureMatrix:
    names = feature_names or DEFAULT_FEATURES
    closes = [float(c.close) for c in candles]
    highs = [float(c.high) for c in candles]
    lows = [float(c.low) for c in candles]
    volumes = [float(c.volume or 0) for c in candles]

    rows: list[dict[str, float]] = []
    targets: list[dict[str, float]] = []
    end = len(candles) - horizon if include_targets else len(candles)
    for i in range(20, max(20, end)):
        row = {
            "return_1": _pct(closes[i], closes[i - 1]),
            "return_3": _pct(closes[i], closes[i - 3]),
            "return_5": _pct(closes[i], closes[i - 5]),
            "return_10": _pct(closes[i], closes[i - 10]),
            "volatility_10": _vol(closes[i - 9 : i + 1]),
            "volatility_20": _vol(closes[i - 19 : i + 1]),
            "range_pct": (highs[i] - lows[i]) / closes[i] if closes[i] else 0.0,
            "volume_change": _pct(volumes[i], volumes[i - 1]) if volumes[i - 1] else 0.0,
            "sma_gap_10": _sma_gap(closes, i, 10),
            "sma_gap_20": _sma_gap(closes, i, 20),
        }
        rows.append({name: _finite(row.get(name, 0.0)) for name in names})
        if include_targets:
            future_return = _pct(closes[i + horizon], closes[i])
            targets.append(
                {
                    "up": 1.0 if future_return > 0 else 0.0,
                    "down": 1.0 if future_return < 0 else 0.0,
                    "expected_return": future_return,
                    "volatility": row["volatility_20"],
                }
            )
    return FeatureMatrix(feature_names=names, rows=rows, targets=targets, horizon=horizon)


def _pct(value: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return _finite((value - previous) / previous)


def _vol(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    returns = [_pct(values[i], values[i - 1]) for i in range(1, len(values))]
    return _finite(pstdev(returns)) if len(returns) > 1 else 0.0


def _sma_gap(values: list[float], index: int, period: int) -> float:
    window = values[index - period + 1 : index + 1]
    avg = mean(window)
    return _pct(values[index], avg)


def _finite(value: float) -> float:
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return float(value)
