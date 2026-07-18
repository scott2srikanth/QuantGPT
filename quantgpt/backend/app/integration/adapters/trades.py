"""OpenAlgo Trades adapter."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.integration.adapters.base import BaseOpenAlgoAdapter
from app.integration.models import Product, Side, TradeRecord


class OpenAlgoTradesAdapter(BaseOpenAlgoAdapter):
    def get_tradebook(self) -> list[TradeRecord]:
        data = self._post("/api/v1/tradebook")
        rows = data if isinstance(data, list) else data.get("trades", [])
        return [self._parse_trade(r) for r in rows]

    def get_trades_for_order(self, order_id: str) -> list[TradeRecord]:
        all_trades = self.get_tradebook()
        return [t for t in all_trades if t.order_id == order_id]

    def _parse_trade(self, r: dict) -> TradeRecord:
        return TradeRecord(
            trade_id=str(r.get("tradeid", r.get("trade_id", ""))),
            order_id=str(r.get("orderid", r.get("order_id", ""))),
            symbol=r.get("symbol", ""),
            exchange=r.get("exchange", ""),
            side=Side(r.get("action", "BUY")),
            quantity=int(r.get("quantity", 0)),
            price=Decimal(str(r.get("price", 0))),
            product=Product(r.get("product", "MIS")),
            strategy=r.get("strategy"),
            timestamp=self._ts(r),
        )

    @staticmethod
    def _ts(r: dict) -> datetime | None:
        ts = r.get("trade_timestamp") or r.get("timestamp")
        if not ts:
            return None
        try:
            return datetime.fromisoformat(str(ts))
        except Exception:
            return None
