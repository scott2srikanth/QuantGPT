"""Auth router: register, login, refresh, logout, me."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.jwt import create_access_token, create_refresh_token, verify_refresh_token
from app.config.settings import get_settings
from app.db.session import get_db
from app.models.models import RefreshToken, User
from app.schemas.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenPair, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
_s = get_settings()


def _h(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def _issue(db: Session, user: User) -> TokenPair:
    access = create_access_token(user.id, [r.name for r in user.roles])
    refresh = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, token_hash=_h(refresh), expires_at=datetime.now(timezone.utc) + timedelta(days=_s.quantgpt_jwt_refresh_ttl_days)))
    db.commit()
    return TokenPair(access_token=access, refresh_token=refresh, expires_in=_s.quantgpt_jwt_access_ttl_minutes * 60)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(p: RegisterRequest, db: Session = Depends(get_db)):
    from app.services.user_service import UserService
    try:
        return UserService().register(db, email=p.email, password=p.password, full_name=p.full_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/login", response_model=TokenPair)
def login(p: LoginRequest, db: Session = Depends(get_db)):
    from app.services.user_service import UserService
    u = UserService().authenticate(db, email=p.email, password=p.password)
    if not u:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    return _issue(db, u)


@router.post("/refresh", response_model=TokenPair)
def refresh(p: RefreshRequest, db: Session = Depends(get_db)):
    try:
        decoded = verify_refresh_token(p.refresh_token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh")
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == _h(p.refresh_token)))
    if not stored or stored.revoked or stored.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh revoked")
    u = db.get(User, uuid.UUID(decoded["sub"]))
    if not u or not u.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user inactive")
    stored.revoked = True
    db.commit()
    return _issue(db, u)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(p: RefreshRequest, db: Session = Depends(get_db)):
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == _h(p.refresh_token)))
    if stored:
        stored.revoked = True
        db.commit()
    return None


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
