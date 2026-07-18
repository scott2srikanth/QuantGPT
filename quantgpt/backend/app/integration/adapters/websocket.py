"""OpenAlgo WebSocket stream adapter.

Connects to the OpenAlgo unified WebSocket proxy (port 8765) as an external
client. QuantGPT never modifies OpenAlgo's WS server — it authenticates,
subscribes, and consumes ticks like any other client.

This adapter is async. It exposes an async iterator over neutral Tick
models. Reconnection and backoff are handled internally.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime
from decimal import Decimal
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

from app.integration.exceptions import BackendAuthError, BackendUnreachableError
from app.integration.models import SubscriptionMode, Tick
from app.logging.config import get_logger

_log = get_logger("app.integration.ws")


class OpenAlgoWebSocketAdapter:
    def __init__(
        self,
        *,
        websocket_url: str,
        api_key: str,
        auth_grace_seconds: int = 15,
        reconnect_delay: float = 1.0,
        max_reconnect_delay: float = 30.0,
    ) -> None:
        self._url = websocket_url
        self._api_key = api_key
        self._auth_grace = auth_grace_seconds
        self._reconnect_delay = reconnect_delay
        self._max_reconnect_delay = max_reconnect_delay
        self._ws: Any = None
        self._connected = asyncio.Event()
        self._subscribed: set[str] = set()
        self._queue: asyncio.Queue[Tick | None] = asyncio.Queue()
        self._recv_task: asyncio.Task | None = None
        self._stopped = False

    async def connect(self) -> None:
        if self._ws is not None:
            return
        delay = self._reconnect_delay
        while not self._stopped:
            try:
                _log.info("ws.connect", url=self._url)
                self._ws = await websockets.connect(self._url)
                await self._authenticate()
                self._connected.set()
                delay = self._reconnect_delay
                return
            except BackendAuthError:
                # auth failures are not transient — propagate immediately
                if self._ws is not None:
                    await self._ws.close()
                    self._ws = None
                raise
            except (OSError, ConnectionClosed) as e:
                _log.warning("ws.connect_failed", error=str(e), retry_in=delay)
                if self._ws is not None:
                    await self._ws.close()
                    self._ws = None
                await asyncio.sleep(delay)
                delay = min(delay * 2, self._max_reconnect_delay)
            except Exception as e:
                _log.exception("ws.connect_error")
                raise BackendUnreachableError(str(e)) from e

    async def _authenticate(self) -> None:
        if not self._api_key:
            raise BackendAuthError("no api key configured for WS auth")
        await self._ws.send(json.dumps({"action": "authenticate", "api_key": self._api_key}))
        try:
            resp = await asyncio.wait_for(self._ws.recv(), timeout=self._auth_grace)
        except asyncio.TimeoutError:
            raise BackendAuthError("WS auth grace window expired")
        data = json.loads(resp)
        if data.get("status") not in ("success", "ok", "authenticated"):
            raise BackendAuthError(f"WS auth rejected: {data}")

    async def subscribe(
        self,
        symbols: list[tuple[str, str]],
        mode: SubscriptionMode = SubscriptionMode.LTP,
    ) -> None:
        await self._connected.wait()
        keys = [f"{exch}:{sym}" for sym, exch in symbols]
        payload = {
            "action": "subscribe",
            "symbols": [{"symbol": s, "exchange": e} for s, e in symbols],
            "mode": mode.value,
        }
        await self._ws.send(json.dumps(payload))
        self._subscribed.update(keys)
        _log.info("ws.subscribed", symbols=keys, mode=mode.value)
        if self._recv_task is None:
            self._recv_task = asyncio.create_task(self._recv_loop())

    async def unsubscribe(self, symbols: list[tuple[str, str]]) -> None:
        if not self._ws:
            return
        payload = {
            "action": "unsubscribe",
            "symbols": [{"symbol": s, "exchange": e} for s, e in symbols],
        }
        await self._ws.send(json.dumps(payload))
        for sym, exch in symbols:
            self._subscribed.discard(f"{exch}:{sym}")

    async def _recv_loop(self) -> None:
        delay = self._reconnect_delay
        while not self._stopped and self._ws is not None:
            try:
                raw = await self._ws.recv()
                data = json.loads(raw)
                tick = self._parse_tick(data)
                if tick is not None:
                    await self._queue.put(tick)
                delay = self._reconnect_delay
            except ConnectionClosed:
                _log.warning("ws.recv_closed", reconnect_in=delay)
                self._connected.clear()
                await asyncio.sleep(delay)
                delay = min(delay * 2, self._max_reconnect_delay)
                await self.connect()
            except Exception:
                _log.exception("ws.recv_error")

    @staticmethod
    def _parse_tick(data: dict) -> Tick | None:
        try:
            return Tick(
                symbol=str(data["symbol"]),
                exchange=str(data["exchange"]),
                ltp=Decimal(str(data["ltp"])),
                timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None,
                volume=int(data["volume"]) if data.get("volume") else None,
            )
        except (KeyError, ValueError):
            return None

    def stream(self) -> AsyncIterator[Tick]:
        async def _gen():
            while not self._stopped:
                item = await self._queue.get()
                if item is None:
                    return
                yield item

        return _gen()

    async def disconnect(self) -> None:
        self._stopped = True
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
        await self._queue.put(None)
        if self._ws:
            await self._ws.close()
            self._ws = None
        self._connected.clear()
