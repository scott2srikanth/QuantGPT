"""OpenAlgo Orders adapter.

Translates OpenAlgo /api/v1/{placeorder, modifyorder, cancelorder, orderbook,
orderstatus} into QuantGPT neutral models.
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
    Product,
    Side,
)


class OpenAlgoOrdersAdapter(BaseOpenAlgoAdapter):
    def place_order(self, request: OrderRequest) -> OrderResponse:
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

    def modify_order(
        self,
        order_id: str,
        *,
        quantity: int | None = None,
        price: Decimal | None = None,
        order_type: str | None = None,
        trigger_price: Decimal | None = None,
    ) -> OrderResponse:
        body: dict = {"orderid": order_id}
        if quantity is not None:
            body["quantity"] = quantity
        if price is not None:
            body["price"] = str(price)
        if order_type is not None:
            body["pricetype"] = order_type
        if trigger_price is not None:
            body["trigger_price"] = str(trigger_price)
        data = self._post("/api/v1/modifyorder", body)
        return OrderResponse(
            order_id=str(data.get("orderid", order_id)),
            status=OrderStatus.COMPLETE,
            timestamp=datetime.now(timezone.utc),
        )

    def cancel_order(self, order_id: str) -> OrderResponse:
        data = self._post("/api/v1/cancelorder", {"orderid": order_id})
        return OrderResponse(
            order_id=str(data.get("orderid", order_id)),
            status=OrderStatus.CANCELLED,
            timestamp=datetime.now(timezone.utc),
        )

    def get_orderbook(self) -> list[OrderRecord]:
        data = self._post("/api/v1/orderbook")
        rows = data if isinstance(data, list) else data.get("orders", [])
        return [self._parse_order(r) for r in rows]

    def get_order(self, order_id: str) -> OrderRecord:
        data = self._post("/api/v1/orderstatus", {"orderid": order_id})
        return self._parse_order(data if isinstance(data, dict) else {"orderid": order_id})

    def _parse_order(self, r: dict) -> OrderRecord:
        return OrderRecord(
            order_id=str(r.get("orderid", "")),
            symbol=r.get("symbol", ""),
            exchange=r.get("exchange", ""),
            side=Side(r.get("action", "BUY")),
            quantity=int(r.get("quantity", 0)),
            product=Product(r.get("product", "MIS")),
            order_type=OrderType(r.get("pricetype", r.get("price_type", "MARKET"))),
            price=Decimal(str(r["price"])) if r.get("price") else None,
            trigger_price=Decimal(str(r["trigger_price"])) if r.get("trigger_price") else None,
            status=OrderStatus(r.get("order_status", r.get("status", "open"))),
            average_price=Decimal(str(r["average_price"])) if r.get("average_price") else None,
            filled_quantity=int(r["filled_quantity"]) if r.get("filled_quantity") else None,
            rejected_reason=r.get("rejection_reason"),
            strategy=r.get("strategy"),
            timestamp=self._ts(r),
        )

    @staticmethod
    def _ts(r: dict) -> datetime | None:
        ts = r.get("order_timestamp") or r.get("update_timestamp") or r.get("timestamp")
        if not ts:
            return None
        try:
            return datetime.fromisoformat(str(ts))
        except Exception:
            return None
