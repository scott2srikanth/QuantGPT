"""Integration router: exposes the OpenAlgo Integration Layer status and proxies."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_roles
from app.core.container import get_container
from app.models.models import User
from app.schemas.schemas import OpenAlgoStatus

router = APIRouter(prefix="/integration", tags=["integration"])


@router.get("/openalgo/status", response_model=OpenAlgoStatus)
def openalgo_status(_: User = Depends(require_roles("admin", "trader", "viewer"))):
    facade = get_container().integration
    s = facade.broker_status()
    return OpenAlgoStatus(base_url=s.base_url, reachable=s.reachable, api_key_configured=s.api_key_configured, websocket_url=s.websocket_url, detail=s.detail)
