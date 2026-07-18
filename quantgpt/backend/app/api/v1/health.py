"""Health router."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.db.session import get_db
from app.schemas.schemas import HealthComponent, HealthDetailResponse, HealthResponse
from app.services.health_service import HealthService

router = APIRouter(prefix="/health", tags=["health"])
_s = get_settings()


@router.get("", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", version="0.1.0", environment=_s.quantgpt_env, timestamp=datetime.now(timezone.utc))


@router.get("/ready", response_model=HealthDetailResponse)
def readiness(db: Session = Depends(get_db)):
    svc = HealthService()
    comps: list[HealthComponent] = []
    db_ok, db_d = svc.check_db(db)
    comps.append(HealthComponent(name="postgres", status="ok" if db_ok else "fail", detail=db_d))
    r_ok, r_d = svc.check_redis(_s.redis_url)
    comps.append(HealthComponent(name="redis", status="ok" if r_ok else "fail", detail=r_d))
    ok = db_ok and r_ok
    code = status.HTTP_200_OK if ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content=HealthDetailResponse(status="ok" if ok else "degraded", version="0.1.0", environment=_s.quantgpt_env, timestamp=datetime.now(timezone.utc), components=comps).model_dump(mode="json"))
