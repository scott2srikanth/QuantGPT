"""OpenAlgo Paper Trading adapter.

OpenAlgo exposes a sandbox/analyzer mode via the same REST endpoints but
routed to its sandbox engine when `analyze_mode` is enabled server-side.
QuantGPT treats paper trading as a distinct capability so callers can
explicitly request paper execution without affecting live orders.

This adapter calls the same OpenAlgo endpoints but is kept separate so
the live Orders adapter never accidentally routes to the sandbox.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.integration.adapters.base import BaseOpenAlgoAdapter
from app.integration.models import (
    OrderRecord,
    OrderRequest,
    OrderResponse,
    OrderStatus,
    OrderType,
    Position,
    Product,
    Side,
)
from app.integration.models import Funds


class OpenAlgoPaperTradingAdapter(BaseOpenAlgoAdapter):
    def place_paper_order(self, request: OrderRequest) -> OrderResponse:
        body = {
            "symbol": request.symbol,
            "exchange": request.exchange,
            "action": request.side.value,
            "quantity": request.quantity,
            "product": request.product.value,
            "pricetype": request.order_type.value,
            "price": str(request.price) if request.price is not None else "",
            "trigger_price": str(request.trigger_price) if request.trigger_price is not None else "",
            "validity": request.validity.value,
            "analyze": True,
        }
        if request.strategy:
            body["strategy"] = request.strategy
        data = self._post("/api/v1/placeorder", body)
        return OrderResponse(
            order_id=str(data.get("orderid", "")),
            status=OrderStatus.COMPLETE if data.get("orderid") else OrderStatus.REJECTED,
            rejected_reason=data.get("message"),
            timestamp=datetime.now(timezone.utc),
        )

    def get_paper_orderbook(self) -> list[OrderRecord]:
        data = self._post("/api/v1/orderbook", {"analyze": True})
        rows = data if isinstance(data, list) else data.get("orders", [])
        return [self._parse_order(r) for r in rows]

    def get_paper_positions(self) -> list[Position]:
        data = self._post("/api/v1/positionbook", {"analyze": True})
        rows = data if isinstance(data, list) else data.get("positions", [])
        return [
            Position(
                symbol=r.get("symbol", ""),
                exchange=r.get("exchange", ""),
                product=Product(r.get("product", "MIS")),
                quantity=int(r.get("quantity", 0)),
                average_price=Decimal(str(r.get("average_price", 0))),
                ltp=Decimal(str(r["ltp"])) if r.get("ltp") else None,
                pnl=Decimal(str(r["pnl"])) if r.get("pnl") else None,
            )
            for r in rows
        ]

    def get_paper_funds(self) -> Funds:
        data = self._post("/api/v1/funds", {"analyze": True})
        return Funds(
            total_capital=Decimal(str(data["total_capital"])) if data.get("total_capital") else None,
            available_balance=Decimal(str(data.get("available_balance", 0))),
            used_margin=Decimal(str(data["used_margin"])) if data.get("used_margin") else None,
        )

    def _parse_order(self, r: dict) -> OrderRecord:
        return OrderRecord(
            order_id=str(r.get("orderid", "")),
            symbol=r.get("symbol", ""),
            exchange=r.get("exchange", ""),
            side=Side(r.get("action", "BUY")),
            quantity=int(r.get("quantity", 0)),
            product=Product(r.get("product", "MIS")),
            order_type=OrderType(r.get("pricetype", "MARKET")),
            status=OrderStatus(r.get("order_status", "open")),
            timestamp=datetime.now(timezone.utc),
        )
