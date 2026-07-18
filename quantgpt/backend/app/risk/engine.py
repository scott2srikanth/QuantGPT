"""Portfolio risk engine and trade approval logic."""

from __future__ import annotations

import math
from statistics import mean, pstdev
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integration.models import Funds, OrderRequest, Position, Product, Side
from app.models.models import RiskApproval, RiskLimitState, RiskPolicy
from app.risk.schemas import (
    CapitalAllocationOut,
    CorrelationMatrixOut,
    PortfolioMetricsOut,
    PositionSizingOut,
    RiskDecision,
)


class RiskRejectedError(RuntimeError):
    def __init__(self, decision: RiskDecision) -> None:
        self.decision = decision
        super().__init__("Trade rejected by Risk Engine: " + "; ".join(decision.reasons))


def get_or_create_default_policy(db: Session | None = None) -> RiskPolicy:
    if db is None:
        return RiskPolicy(
            name="default",
            is_active=True,
            max_position_notional=100000.0,
            max_order_notional=50000.0,
            max_portfolio_heat=0.06,
            max_symbol_exposure_pct=0.15,
            max_sector_exposure_pct=0.30,
            max_gross_exposure_pct=1.0,
            max_loss_per_trade_pct=0.01,
            daily_stop_loss_pct=0.03,
            weekly_stop_loss_pct=0.06,
            monthly_stop_loss_pct=0.10,
            max_drawdown_pct=0.15,
            correlation_limit=0.85,
            metadata_={},
        )
    row = db.scalar(select(RiskPolicy).where(RiskPolicy.is_active.is_(True)).order_by(RiskPolicy.created_at.desc()))
    if row:
        return row
    row = RiskPolicy(name="default", metadata_={"created_by": "risk_engine"})
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


class RiskEngine:
    def __init__(
        self,
        *,
        db: Session | None = None,
        policy: RiskPolicy | None = None,
        positions_provider: Callable[[], list[Position]] | None = None,
        funds_provider: Callable[[], Funds] | None = None,
        price_provider: Callable[[str, str], float] | None = None,
    ) -> None:
        self.db = db
        self.policy = policy or get_or_create_default_policy(db)
        self.positions_provider = positions_provider
        self.funds_provider = funds_provider
        self.price_provider = price_provider

    def approve_order(
        self,
        order: OrderRequest,
        *,
        estimated_price: float | None = None,
        sector: str | None = None,
        persist: bool = True,
    ) -> RiskDecision:
        price = estimated_price or self._price(order)
        reasons: list[str] = []
        checks: dict = {}
        if price <= 0:
            reasons.append("Unable to price order; live trades fail closed.")
        notional = max(float(order.quantity) * max(price, 0.0), 0.0)
        positions = self._positions()
        equity = self._equity()
        portfolio = portfolio_metrics(positions, equity=equity, policy=self.policy)

        checks["order_notional"] = {"value": notional, "limit": self.policy.max_order_notional}
        if notional > self.policy.max_order_notional:
            reasons.append("Order notional exceeds maximum order limit.")

        projected_symbol = _symbol_exposure(positions, order.symbol) + (notional if order.side == Side.BUY else -notional)
        checks["symbol_exposure_pct"] = {
            "value": abs(projected_symbol) / equity if equity else 1.0,
            "limit": self.policy.max_symbol_exposure_pct,
        }
        if checks["symbol_exposure_pct"]["value"] > self.policy.max_symbol_exposure_pct:
            reasons.append("Projected symbol exposure exceeds limit.")

        projected_gross = portfolio.gross_exposure + notional
        checks["gross_exposure_pct"] = {
            "value": projected_gross / equity if equity else 1.0,
            "limit": self.policy.max_gross_exposure_pct,
        }
        if checks["gross_exposure_pct"]["value"] > self.policy.max_gross_exposure_pct:
            reasons.append("Projected gross exposure exceeds limit.")

        checks["portfolio_heat"] = {"value": portfolio.portfolio_heat, "limit": self.policy.max_portfolio_heat}
        if portfolio.portfolio_heat > self.policy.max_portfolio_heat:
            reasons.append("Portfolio heat exceeds limit.")

        checks["drawdown_pct"] = {"value": portfolio.drawdown_pct, "limit": self.policy.max_drawdown_pct}
        if portfolio.drawdown_pct > self.policy.max_drawdown_pct:
            reasons.append("Maximum drawdown limit breached.")

        if portfolio.daily_stop_triggered:
            reasons.append("Daily stop is triggered.")
        if portfolio.weekly_stop_triggered:
            reasons.append("Weekly stop is triggered.")
        if portfolio.monthly_stop_triggered:
            reasons.append("Monthly stop is triggered.")
        if portfolio.max_loss_triggered:
            reasons.append("Maximum loss threshold is triggered.")

        if sector:
            sector_alloc = portfolio.sector_allocation.get(sector, 0.0) + (notional / equity if equity else 1.0)
            checks["sector_exposure_pct"] = {"value": sector_alloc, "limit": self.policy.max_sector_exposure_pct}
            if sector_alloc > self.policy.max_sector_exposure_pct:
                reasons.append("Projected sector allocation exceeds limit.")

        confidence = _confidence(checks, reasons)
        approved = not reasons
        decision = RiskDecision(
            approved=approved,
            status="approved" if approved else "rejected",
            confidence_score=confidence,
            reasons=reasons,
            checks=checks,
        )
        if persist and self.db is not None:
            approval = RiskApproval(
                policy_id=self.policy.id,
                status=decision.status,
                symbol=order.symbol,
                exchange=order.exchange,
                side=order.side.value,
                quantity=order.quantity,
                estimated_price=price,
                notional=notional,
                confidence_score=confidence,
                reasons=reasons,
                checks=checks,
                request=order.model_dump(mode="json"),
            )
            self.db.add(approval)
            self.db.commit()
            self.db.refresh(approval)
            decision.approval_id = approval.id
        return decision

    def enforce_order(self, order: OrderRequest) -> RiskDecision:
        decision = self.approve_order(order, persist=False)
        if not decision.approved:
            raise RiskRejectedError(decision)
        return decision

    def _positions(self) -> list[Position]:
        if not self.positions_provider:
            return []
        try:
            return self.positions_provider()
        except Exception:
            return []

    def _equity(self) -> float:
        if not self.funds_provider:
            return 100000.0
        try:
            funds = self.funds_provider()
            return float(funds.available_balance + (funds.used_margin or 0))
        except Exception:
            return 100000.0

    def _price(self, order: OrderRequest) -> float:
        if order.price is not None:
            return float(order.price)
        if self.price_provider:
            try:
                return float(self.price_provider(order.symbol, order.exchange))
            except Exception:
                return 0.0
        return 0.0


def position_size(
    *,
    account_equity: float,
    entry_price: float,
    stop_price: float,
    risk_pct: float,
    max_notional: float | None = None,
) -> PositionSizingOut:
    per_unit_risk = abs(entry_price - stop_price)
    risk_amount = account_equity * risk_pct
    quantity = int(risk_amount / per_unit_risk) if per_unit_risk else 0
    notional = quantity * entry_price
    capped = False
    if max_notional and notional > max_notional:
        quantity = int(max_notional / entry_price)
        notional = quantity * entry_price
        capped = True
    return PositionSizingOut(
        quantity=max(quantity, 0),
        risk_amount=risk_amount,
        notional=notional,
        per_unit_risk=per_unit_risk,
        capped_by_notional=capped,
    )


def portfolio_metrics(
    positions: list[Position],
    *,
    equity: float,
    policy: RiskPolicy,
    sectors: dict[str, str] | None = None,
) -> PortfolioMetricsOut:
    sectors = sectors or {}
    gross = 0.0
    net = 0.0
    symbol_exposure: dict[str, float] = {}
    sector_notional: dict[str, float] = {}
    for pos in positions:
        price = float(pos.ltp or pos.average_price)
        notional = float(pos.quantity) * price
        gross += abs(notional)
        net += notional
        symbol_exposure[pos.symbol] = symbol_exposure.get(pos.symbol, 0.0) + abs(notional)
        sector = sectors.get(pos.symbol, "unknown")
        sector_notional[sector] = sector_notional.get(sector, 0.0) + abs(notional)

    heat = sum(abs(float(pos.pnl or 0.0)) for pos in positions) / equity if equity else 1.0
    drawdown = _drawdown_pct(equity, policy)
    sector_allocation = {key: value / equity for key, value in sector_notional.items()} if equity else {}
    symbol_pct = {key: value / equity for key, value in symbol_exposure.items()} if equity else {}
    return PortfolioMetricsOut(
        gross_exposure=gross,
        net_exposure=net,
        capital_allocated_pct=gross / equity if equity else 1.0,
        portfolio_heat=heat,
        drawdown_pct=drawdown,
        sector_allocation=sector_allocation,
        symbol_exposure=symbol_pct,
        daily_stop_triggered=False,
        weekly_stop_triggered=False,
        monthly_stop_triggered=False,
        max_loss_triggered=heat > policy.max_loss_per_trade_pct,
    )


def correlation_matrix(returns: dict[str, list[float]]) -> CorrelationMatrixOut:
    symbols = list(returns)
    matrix = [[_corr(returns[a], returns[b]) for b in symbols] for a in symbols]
    return CorrelationMatrixOut(symbols=symbols, matrix=matrix)


def capital_allocation(
    expected_returns: dict[str, float],
    volatility: dict[str, float],
    *,
    max_weight: float,
) -> CapitalAllocationOut:
    scores = {
        symbol: max(ret, 0.0) / max(volatility.get(symbol, 0.0), 0.0001)
        for symbol, ret in expected_returns.items()
    }
    total = sum(scores.values()) or 1.0
    raw = {symbol: score / total for symbol, score in scores.items()}
    capped = {symbol: min(weight, max_weight) for symbol, weight in raw.items()}
    norm = sum(capped.values()) or 1.0
    return CapitalAllocationOut(weights={symbol: weight / norm for symbol, weight in capped.items()}, method="risk_adjusted_capped")


def _symbol_exposure(positions: list[Position], symbol: str) -> float:
    total = 0.0
    for pos in positions:
        if pos.symbol == symbol:
            total += float(pos.quantity) * float(pos.ltp or pos.average_price)
    return total


def _drawdown_pct(equity: float, policy: RiskPolicy) -> float:
    metadata = policy.metadata_ or {}
    peak = float(metadata.get("peak_equity", equity) or equity)
    if peak <= 0:
        return 0.0
    return max((peak - equity) / peak, 0.0)


def _corr(a: list[float], b: list[float]) -> float:
    size = min(len(a), len(b))
    if size < 2:
        return 0.0
    aa = a[-size:]
    bb = b[-size:]
    ma = mean(aa)
    mb = mean(bb)
    denom = (pstdev(aa) * pstdev(bb))
    if denom == 0:
        return 0.0
    return max(-1.0, min(1.0, sum((x - ma) * (y - mb) for x, y in zip(aa, bb, strict=False)) / (size * denom)))


def _confidence(checks: dict, reasons: list[str]) -> float:
    if reasons:
        return 0.95
    margins = []
    for check in checks.values():
        limit = check.get("limit")
        value = abs(check.get("value", 0.0))
        if limit:
            margins.append(max((limit - value) / limit, 0.0))
    return max(0.1, min(0.95, mean(margins) if margins else 0.5))
