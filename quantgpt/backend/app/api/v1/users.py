"""Users + roles router (admin-only)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import RoleAssignRequest, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    from app.services.user_service import UserService
    return UserService().list_users(db)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_roles("admin", "trader", "viewer"))):
    from app.services.user_service import UserService
    u = UserService().get(db, user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return u


@router.post("/{user_id}/roles", response_model=UserOut)
def assign_role(user_id: uuid.UUID, p: RoleAssignRequest, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    from app.services.user_service import UserService
    try:
        return UserService().assign_role(db, user_id, p.role_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{user_id}/roles/{role_name}", response_model=UserOut)
def revoke_role(user_id: uuid.UUID, role_name: str, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    from app.services.user_service import UserService
    try:
        return UserService().revoke_role(db, user_id, role_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
