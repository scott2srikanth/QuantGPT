"""Risk engine API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import roles as rc
from app.auth.dependencies import require_roles
from app.core.container import get_container
from app.db.session import get_db
from app.models.models import RiskApproval, RiskPolicy, User
from app.risk.engine import (
    RiskEngine,
    capital_allocation,
    correlation_matrix,
    get_or_create_default_policy,
    portfolio_metrics,
    position_size,
)
from app.risk.schemas import (
    CapitalAllocationOut,
    CapitalAllocationRequest,
    CorrelationMatrixOut,
    CorrelationMatrixRequest,
    PortfolioMetricsOut,
    PositionSizingOut,
    PositionSizingRequest,
    RiskApprovalOut,
    RiskDecision,
    RiskEvaluationRequest,
    RiskPolicyIn,
    RiskPolicyOut,
)

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/policy", response_model=RiskPolicyOut)
def get_policy(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(rc.ADMIN, rc.TRADER, rc.VIEWER)),
):
    return get_or_create_default_policy(db)


@router.put("/policy", response_model=RiskPolicyOut)
def upsert_policy(
    payload: RiskPolicyIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(rc.ADMIN)),
):
    current = db.scalar(select(RiskPolicy).where(RiskPolicy.name == payload.name))
    if current is None:
        current = RiskPolicy(name=payload.name)
        db.add(current)
    for key, value in payload.model_dump(exclude={"metadata"}).items():
        setattr(current, key, value)
    current.metadata_ = payload.metadata
    db.commit()
    db.refresh(current)
    return current


@router.post("/evaluate", response_model=RiskDecision)
def evaluate_trade(
    payload: RiskEvaluationRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(rc.ADMIN, rc.TRADER)),
):
    facade = _facade_or_none()
    engine = RiskEngine(
        db=db,
        positions_provider=facade.positions if facade else None,
        funds_provider=facade.funds if facade else None,
        price_provider=(lambda symbol, exchange: float(facade.quote(symbol, exchange).ltp)) if facade else None,
    )
    return engine.approve_order(
        payload.order,
        estimated_price=payload.estimated_price,
        sector=payload.sector,
    )


@router.get("/approvals", response_model=list[RiskApprovalOut])
def list_approvals(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(rc.ADMIN, rc.TRADER, rc.VIEWER)),
):
    return db.scalars(select(RiskApproval).order_by(RiskApproval.created_at.desc()).limit(100)).all()


@router.post("/position-size", response_model=PositionSizingOut)
def calculate_position_size(
    payload: PositionSizingRequest,
    _: User = Depends(require_roles(rc.ADMIN, rc.TRADER, rc.VIEWER)),
):
    return position_size(**payload.model_dump())


@router.get("/portfolio", response_model=PortfolioMetricsOut)
def get_portfolio_risk(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(rc.ADMIN, rc.TRADER, rc.VIEWER)),
):
    facade = _facade_or_none()
    policy = get_or_create_default_policy(db)
    if facade:
        try:
            positions = facade.positions()
            funds = facade.funds()
            equity = float(funds.available_balance + (funds.used_margin or 0))
        except Exception:
            positions = []
            equity = 100000.0
    else:
        positions = []
        equity = 100000.0
    return portfolio_metrics(positions, equity=equity, policy=policy)


@router.post("/correlation", response_model=CorrelationMatrixOut)
def get_correlation_matrix(
    payload: CorrelationMatrixRequest,
    _: User = Depends(require_roles(rc.ADMIN, rc.TRADER, rc.VIEWER)),
):
    return correlation_matrix(payload.returns)


@router.post("/capital-allocation", response_model=CapitalAllocationOut)
def get_capital_allocation(
    payload: CapitalAllocationRequest,
    _: User = Depends(require_roles(rc.ADMIN, rc.TRADER, rc.VIEWER)),
):
    return capital_allocation(
        payload.expected_returns,
        payload.volatility,
        max_weight=payload.max_weight,
    )


def _facade_or_none():
    try:
        return get_container().integration
    except Exception:
        return None
