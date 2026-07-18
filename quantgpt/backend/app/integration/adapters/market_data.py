"""OpenAlgo Market Data adapter.

Translates OpenAlgo /api/v1/{quotes, multiquotes, depth, history, search,
optionchain, instruments} responses into QuantGPT neutral models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.integration.adapters.base import BaseOpenAlgoAdapter
from app.integration.models import (
    Candle,
    DepthLevel,
    Instrument,
    MarketDepth,
    OptionChain,
    OptionChainEntry,
    Quote,
)


class OpenAlgoMarketDataAdapter(BaseOpenAlgoAdapter):
    def get_quote(self, symbol: str, exchange: str) -> Quote:
        key = f"quote:{exchange}:{symbol}"
        return self._cached(
            key,
            lambda: self._quote_one(symbol, exchange),
        )

    def _quote_one(self, symbol: str, exchange: str) -> Quote:
        data = self._post("/api/v1/quotes", {"symbols": symbol, "exchange": exchange})
        # OpenAlgo returns {symbol: {...}} keyed by symbol
        entry = self._pick(data, symbol)
        return self._parse_quote(entry, symbol, exchange)

    def get_quotes(self, symbols: list[tuple[str, str]]) -> list[Quote]:
        # OpenAlgo multiquotes expects a single exchange + comma-separated symbols.
        # For simplicity (and because most callers use one exchange), group by exchange.
        out: list[Quote] = []
        by_exchange: dict[str, list[str]] = {}
        for sym, exch in symbols:
            by_exchange.setdefault(exch, []).append(sym)
        for exch, syms in by_exchange.items():
            data = self._post("/api/v1/multiquotes", {"symbols": ",".join(syms), "exchange": exch})
            for sym in syms:
                entry = self._pick(data, sym)
                out.append(self._parse_quote(entry, sym, exch))
        return out

    def get_depth(self, symbol: str, exchange: str) -> MarketDepth:
        data = self._post("/api/v1/depth", {"symbol": symbol, "exchange": exchange})
        entry = self._pick(data, symbol)
        bids = [DepthLevel(price=Decimal(str(b["price"])), quantity=int(b["quantity"]), orders=b.get("orders")) for b in entry.get("bids", [])]
        asks = [DepthLevel(price=Decimal(str(a["price"])), quantity=int(a["quantity"]), orders=a.get("orders")) for a in entry.get("asks", [])]
        return MarketDepth(symbol=symbol, exchange=exchange, bids=bids, asks=asks, timestamp=self._ts(entry))

    def get_history(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        *,
        start: str | None = None,
        end: str | None = None,
        limit: int = 100,
    ) -> list[Candle]:
        body = {"symbol": symbol, "exchange": exchange, "interval": interval}
        if start:
            body["start_date"] = start
        if end:
            body["end_date"] = end
        data = self._post("/api/v1/history", body)
        rows = data if isinstance(data, list) else data.get("candles", [])
        candles = [
            Candle(
                timestamp=datetime.fromisoformat(r["timestamp"]) if "timestamp" in r else datetime.now(timezone.utc),
                open=Decimal(str(r["open"])),
                high=Decimal(str(r["high"])),
                low=Decimal(str(r["low"])),
                close=Decimal(str(r["close"])),
                volume=int(r["volume"]) if "volume" in r else None,
            )
            for r in rows[-limit:]
        ]
        return candles

    def search_instruments(self, query: str) -> list[Instrument]:
        key = f"search:{query}"
        return self._cached(
            key,
            lambda: self._search(query),
        )

    def _search(self, query: str) -> list[Instrument]:
        data = self._get("/api/v1/search", {"query": query})
        rows = data if isinstance(data, list) else data.get("instruments", [])
        return [self._parse_instrument(r) for r in rows]

    def get_option_chain(self, symbol: str, exchange: str) -> OptionChain:
        key = f"optionchain:{exchange}:{symbol}"
        return self._cached(
            key,
            lambda: self._option_chain(symbol, exchange),
        )

    def _option_chain(self, symbol: str, exchange: str) -> OptionChain:
        data = self._post("/api/v1/optionchain", {"symbol": symbol, "exchange": exchange})
        underlying = data.get("underlying_ltp")
        strikes_raw = data.get("strikes", [])
        strikes = [OptionChainEntry(strike=Decimal(str(s["strike"])), ce=self._parse_quote(s.get("ce"), "", exchange) if s.get("ce") else None, pe=self._parse_quote(s.get("pe"), "", exchange) if s.get("pe") else None) for s in strikes_raw]
        return OptionChain(symbol=symbol, exchange=exchange, underlying_ltp=Decimal(str(underlying)) if underlying else None, strikes=strikes)

    # ── parsers ──
    def _parse_quote(self, entry: dict, symbol: str, exchange: str) -> Quote:
        if not entry:
            return Quote(symbol=symbol, exchange=exchange, ltp=Decimal("0"))
        return Quote(
            symbol=symbol,
            exchange=exchange,
            ltp=Decimal(str(entry.get("ltp", 0))),
            open=Decimal(str(entry["open"])) if "open" in entry else None,
            high=Decimal(str(entry["high"])) if "high" in entry else None,
            low=Decimal(str(entry["low"])) if "low" in entry else None,
            close=Decimal(str(entry["close"])) if "close" in entry else None,
            volume=int(entry["volume"]) if "volume" in entry else None,
            timestamp=self._ts(entry),
        )

    def _parse_instrument(self, r: dict) -> Instrument:
        return Instrument(
            symbol=r.get("symbol", ""),
            exchange=r.get("exchange", ""),
            token=r.get("token"),
            name=r.get("name"),
            instrument_type=r.get("instrument_type"),
            expiry=datetime.fromisoformat(r["expiry"]) if r.get("expiry") else None,
            strike=Decimal(str(r["strike"])) if r.get("strike") else None,
            lot_size=int(r["lot_size"]) if r.get("lot_size") else None,
        )

    @staticmethod
    def _pick(data: dict, symbol: str) -> dict:
        if isinstance(data, dict):
            if symbol in data:
                return data[symbol]
            # OpenAlgo sometimes nests under data/symbol
            for v in data.values():
                if isinstance(v, dict) and v.get("symbol") == symbol:
                    return v
            # fallback: first dict value
            for v in data.values():
                if isinstance(v, dict):
                    return v
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _ts(entry: dict) -> datetime | None:
        ts = entry.get("timestamp") or entry.get("last_trade_time")
        if not ts:
            return None
        try:
            return datetime.fromisoformat(str(ts))
        except Exception:
            return None
