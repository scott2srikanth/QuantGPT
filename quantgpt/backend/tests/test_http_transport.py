"""Tests for HttpTransport error translation + retry (using a mock httpx client)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.integration.exceptions import (
    BackendAuthError,
    BackendNotFoundError,
    BackendRateLimitError,
    BackendServerError,
    BackendTimeoutError,
    BackendUnreachableError,
    BackendValidationError,
)
from app.integration.http_transport import HttpTransport


def _make_transport_with_client(client: httpx.Client) -> HttpTransport:
    t = HttpTransport(base_url="http://openalgo.test", timeout=1.0, max_retries=2)
    t._client = client
    return t


def _mock_response(status: int, json_data: dict | None = None, text: str = "") -> httpx.Response:
    r = MagicMock(spec=httpx.Response)
    r.status_code = status
    r.text = text or (str(json_data) if json_data else "")
    r.json.return_value = json_data or {}
    return r


def test_success():
    client = MagicMock(spec=httpx.Client)
    client.request.return_value = _mock_response(200, {"status": "success", "data": {"ok": True}})
    t = _make_transport_with_client(client)
    assert t.post("/x") == {"status": "success", "data": {"ok": True}}


def test_401_translates_to_auth_error():
    client = MagicMock(spec=httpx.Client)
    client.request.return_value = _mock_response(401, text="unauthorized")
    t = _make_transport_with_client(client)
    with pytest.raises(BackendAuthError):
        t.post("/x")


def test_404_translates_to_not_found():
    client = MagicMock(spec=httpx.Client)
    client.request.return_value = _mock_response(404, text="nope")
    t = _make_transport_with_client(client)
    with pytest.raises(BackendNotFoundError):
        t.get("/x")


def test_429_translates_to_rate_limit():
    client = MagicMock(spec=httpx.Client)
    client.request.return_value = _mock_response(429, text="slow down")
    t = _make_transport_with_client(client)
    with pytest.raises(BackendRateLimitError):
        t.post("/x")


def test_400_translates_to_validation():
    client = MagicMock(spec=httpx.Client)
    client.request.return_value = _mock_response(400, text="bad")
    t = _make_transport_with_client(client)
    with pytest.raises(BackendValidationError):
        t.post("/x")


def test_500_translates_to_server_error():
    client = MagicMock(spec=httpx.Client)
    client.request.return_value = _mock_response(500, text="boom")
    t = _make_transport_with_client(client)
    with pytest.raises(BackendServerError):
        t.post("/x")


def test_connect_error_translates_to_unreachable():
    client = MagicMock(spec=httpx.Client)
    client.request.side_effect = httpx.ConnectError("refused")
    t = _make_transport_with_client(client)
    with pytest.raises(BackendUnreachableError):
        t.post("/x")


def test_timeout_translates():
    client = MagicMock(spec=httpx.Client)
    client.request.side_effect = httpx.ReadTimeout("slow")
    t = _make_transport_with_client(client)
    with pytest.raises(BackendTimeoutError):
        t.post("/x")


def test_invalid_json_translates_to_server_error():
    client = MagicMock(spec=httpx.Client)
    r = _mock_response(200)
    r.json.side_effect = ValueError("not json")
    client.request.return_value = r
    t = _make_transport_with_client(client)
    with pytest.raises(BackendServerError):
        t.post("/x")
