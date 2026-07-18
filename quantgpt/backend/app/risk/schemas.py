"""Schemas for risk management."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.integration.models import OrderRequest


class RiskPolicyIn(BaseModel):
    name: str = Field(default="default", min_length=1, max_length=255)
    is_active: bool = True
    max_position_notional: float = Field(default=100000.0, gt=0)
    max_order_notional: float = Field(default=50000.0, gt=0)
    max_portfolio_heat: float = Field(default=0.06, gt=0, le=1)
    max_symbol_exposure_pct: float = Field(default=0.15, gt=0, le=1)
    max_sector_exposure_pct: float = Field(default=0.30, gt=0, le=1)
    max_gross_exposure_pct: float = Field(default=1.0, gt=0)
    max_loss_per_trade_pct: float = Field(default=0.01, gt=0, le=1)
    daily_stop_loss_pct: float = Field(default=0.03, gt=0, le=1)
    weekly_stop_loss_pct: float = Field(default=0.06, gt=0, le=1)
    monthly_stop_loss_pct: float = Field(default=0.10, gt=0, le=1)
    max_drawdown_pct: float = Field(default=0.15, gt=0, le=1)
    correlation_limit: float = Field(default=0.85, gt=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RiskPolicyOut(RiskPolicyIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    metadata: dict[str, Any] = Field(validation_alias="metadata_", serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime


class RiskEvaluationRequest(BaseModel):
    order: OrderRequest
    estimated_price: float | None = Field(default=None, gt=0)
    sector: str | None = None
    account_equity: float | None = Field(default=None, gt=0)


class RiskApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    policy_id: uuid.UUID | None
    status: str
    symbol: str
    exchange: str
    side: str
    quantity: int
    estimated_price: float
    notional: float
    confidence_score: float
    reasons: list[str]
    checks: dict[str, Any]
    request: dict[str, Any]
    created_at: datetime


class RiskDecision(BaseModel):
    approved: bool
    status: str
    confidence_score: float = Field(ge=0, le=1)
    reasons: list[str] = Field(default_factory=list)
    checks: dict[str, Any] = Field(default_factory=dict)
    approval_id: uuid.UUID | None = None


class PositionSizingRequest(BaseModel):
    account_equity: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    stop_price: float = Field(gt=0)
    risk_pct: float = Field(default=0.01, gt=0, le=1)
    max_notional: float | None = Field(default=None, gt=0)


class PositionSizingOut(BaseModel):
    quantity: int
    risk_amount: float
    notional: float
    per_unit_risk: float
    capped_by_notional: bool


class PortfolioMetricsOut(BaseModel):
    gross_exposure: float
    net_exposure: float
    capital_allocated_pct: float
    portfolio_heat: float
    drawdown_pct: float
    sector_allocation: dict[str, float]
    symbol_exposure: dict[str, float]
    daily_stop_triggered: bool
    weekly_stop_triggered: bool
    monthly_stop_triggered: bool
    max_loss_triggered: bool


class CorrelationMatrixRequest(BaseModel):
    returns: dict[str, list[float]]


class CorrelationMatrixOut(BaseModel):
    symbols: list[str]
    matrix: list[list[float]]


class CapitalAllocationRequest(BaseModel):
    expected_returns: dict[str, float]
    volatility: dict[str, float]
    max_weight: float = Field(default=0.25, gt=0, le=1)


class CapitalAllocationOut(BaseModel):
    weights: dict[str, float]
    method: str
