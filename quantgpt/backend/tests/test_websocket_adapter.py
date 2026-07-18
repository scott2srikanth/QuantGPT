"""Tests for OpenAlgoWebSocketAdapter (mocked websockets)."""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integration.adapters.websocket import OpenAlgoWebSocketAdapter
from app.integration.exceptions import BackendAuthError
from app.integration.models import SubscriptionMode


@pytest.mark.asyncio
async def test_connect_and_authenticate():
    a = OpenAlgoWebSocketAdapter(websocket_url="ws://test", api_key="key")
    mock_ws = AsyncMock()
    mock_ws.recv.return_value = json.dumps({"status": "success"})
    with patch("app.integration.adapters.websocket.websockets.connect", new=AsyncMock(return_value=mock_ws)):
        await a.connect()
    mock_ws.send.assert_any_call(json.dumps({"action": "authenticate", "api_key": "key"}))
    await a.disconnect()


@pytest.mark.asyncio
async def test_auth_failure_raises():
    a = OpenAlgoWebSocketAdapter(websocket_url="ws://test", api_key="key")
    mock_ws = AsyncMock()
    mock_ws.recv.return_value = json.dumps({"status": "error", "message": "bad key"})
    with patch("app.integration.adapters.websocket.websockets.connect", new=AsyncMock(return_value=mock_ws)):
        with pytest.raises(BackendAuthError):
            await a.connect()


@pytest.mark.asyncio
async def test_auth_timeout_raises():
    a = OpenAlgoWebSocketAdapter(websocket_url="ws://test", api_key="key", auth_grace_seconds=0)
    mock_ws = AsyncMock()
    mock_ws.recv.side_effect = asyncio.TimeoutError
    with patch("app.integration.adapters.websocket.websockets.connect", new=AsyncMock(return_value=mock_ws)):
        with pytest.raises(BackendAuthError):
            await a.connect()


@pytest.mark.asyncio
async def test_subscribe_sends_payload():
    a = OpenAlgoWebSocketAdapter(websocket_url="ws://test", api_key="key")
    mock_ws = AsyncMock()
    mock_ws.recv.return_value = json.dumps({"status": "success"})
    with patch("app.integration.adapters.websocket.websockets.connect", new=AsyncMock(return_value=mock_ws)):
        await a.connect()
        await a.subscribe([("RELIANCE", "NSE")], mode=SubscriptionMode.QUOTE)
    # second send should be the subscribe payload
    calls = [json.loads(c.args[0]) for c in mock_ws.send.call_args_list]
    sub = [c for c in calls if c.get("action") == "subscribe"][0]
    assert sub["mode"] == "quote"
    assert sub["symbols"][0]["symbol"] == "RELIANCE"
    await a.disconnect()


@pytest.mark.asyncio
async def test_parse_tick():
    data = {"symbol": "X", "exchange": "NSE", "ltp": "100.5", "timestamp": "2026-07-18T09:15:00", "volume": 1000}
    tick = OpenAlgoWebSocketAdapter._parse_tick(data)
    assert tick is not None
    assert tick.ltp == Decimal("100.5")
    assert tick.volume == 1000


@pytest.mark.asyncio
async def test_parse_tick_invalid_returns_none():
    assert OpenAlgoWebSocketAdapter._parse_tick({"bad": "data"}) is None
    assert OpenAlgoWebSocketAdapter._parse_tick({}) is None
