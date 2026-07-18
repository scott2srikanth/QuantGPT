import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.config.settings import get_settings

_s = get_settings()
ALGO = _s.quantgpt_jwt_algorithm
SECRET = _s.quantgpt_jwt_secret
ACCESS_TTL = timedelta(minutes=_s.quantgpt_jwt_access_ttl_minutes)
REFRESH_TTL = timedelta(days=_s.quantgpt_jwt_refresh_ttl_days)


def create_access_token(user_id: uuid.UUID, roles: list[str]) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "roles": roles, "type": "access", "iat": int(now.timestamp()), "exp": int((now + ACCESS_TTL).timestamp())}, SECRET, algorithm=ALGO)


def create_refresh_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "type": "refresh", "jti": uuid.uuid4().hex, "iat": int(now.timestamp()), "exp": int((now + REFRESH_TTL).timestamp())}, SECRET, algorithm=ALGO)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, SECRET, algorithms=[ALGO])


def verify_access_token(token: str) -> dict[str, Any]:
    p = decode_token(token)
    if p.get("type") != "access":
        raise JWTError("not an access token")
    return p


def verify_refresh_token(token: str) -> dict[str, Any]:
    p = decode_token(token)
    if p.get("type") != "refresh":
        raise JWTError("not a refresh token")
    return p
