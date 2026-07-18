import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.jwt import verify_access_token
from app.db.session import get_db
from app.models.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

CRED_EXC = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
FORBID_EXC = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if not token:
        raise CRED_EXC
    try:
        payload = verify_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except Exception:
        raise CRED_EXC
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise CRED_EXC
    return user


def require_roles(*roles: str):
    allowed = set(roles)

    def _dep(user: User = Depends(get_current_user)) -> User:
        if not ({r.name for r in user.roles} & allowed):
            raise FORBID_EXC
        return user

    return _dep
