"""OpenAlgo Portfolio adapter (holdings + funds)."""

from __future__ import annotations

from decimal import Decimal

from app.integration.adapters.base import BaseOpenAlgoAdapter
from app.integration.models import Funds, Holding


class OpenAlgoPortfolioAdapter(BaseOpenAlgoAdapter):
    def get_holdings(self) -> list[Holding]:
        data = self._post("/api/v1/holdings")
        rows = data if isinstance(data, list) else data.get("holdings", [])
        return [self._parse_holding(r) for r in rows]

    def get_funds(self) -> Funds:
        data = self._post("/api/v1/funds")
        return Funds(
            total_capital=Decimal(str(data["total_capital"])) if data.get("total_capital") else None,
            available_balance=Decimal(str(data.get("available_balance", data.get("available_margin", 0)))),
            used_margin=Decimal(str(data["used_margin"])) if data.get("used_margin") else None,
            realized_pnl=Decimal(str(data["realized_pnl"])) if data.get("realized_pnl") else None,
            unrealized_pnl=Decimal(str(data["unrealized_pnl"])) if data.get("unrealized_pnl") else None,
        )

    def _parse_holding(self, r: dict) -> Holding:
        return Holding(
            symbol=r.get("symbol", ""),
            exchange=r.get("exchange", ""),
            quantity=int(r.get("quantity", 0)),
            average_price=Decimal(str(r.get("average_price", r.get("avg_price", 0)))),
            ltp=Decimal(str(r["ltp"])) if r.get("ltp") else None,
            pnl=Decimal(str(r["pnl"])) if r.get("pnl") else None,
        )
