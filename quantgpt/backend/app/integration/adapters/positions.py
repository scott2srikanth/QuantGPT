"""OpenAlgo Positions adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.integration.adapters.base import BaseOpenAlgoAdapter
from app.integration.models import (
    OrderResponse,
    OrderStatus,
    Position,
    Product,
)


class OpenAlgoPositionsAdapter(BaseOpenAlgoAdapter):
    def get_positions(self) -> list[Position]:
        data = self._post("/api/v1/positionbook")
        rows = data if isinstance(data, list) else data.get("positions", [])
        return [self._parse_position(r) for r in rows]

    def close_position(self, symbol: str, exchange: str, product: str) -> OrderResponse:
        data = self._post("/api/v1/closeposition", {"symbol": symbol, "exchange": exchange, "product": product})
        return OrderResponse(
            order_id=str(data.get("orderid", "")),
            status=OrderStatus.COMPLETE if data.get("orderid") else OrderStatus.REJECTED,
            rejected_reason=data.get("message"),
            timestamp=datetime.now(timezone.utc),
        )

    def _parse_position(self, r: dict) -> Position:
        return Position(
            symbol=r.get("symbol", ""),
            exchange=r.get("exchange", ""),
            product=Product(r.get("product", "MIS")),
            quantity=int(r.get("quantity", r.get("net_quantity", 0))),
            average_price=Decimal(str(r.get("average_price", r.get("avg_price", 0)))),
            ltp=Decimal(str(r["ltp"])) if r.get("ltp") else None,
            pnl=Decimal(str(r["pnl"])) if r.get("pnl") else None,
            pnl_percent=Decimal(str(r["pnl_percent"])) if r.get("pnl_percent") else None,
        )
