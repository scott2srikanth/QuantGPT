from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.passwords import hash_password, verify_password
from app.auth.roles import is_valid_role
from app.logging.config import get_logger
from app.models.models import Role, User

_log = get_logger("app.services.user")


class UserService:
    def register(self, db: Session, *, email: str, password: str, full_name: str | None) -> User:
        if db.scalar(select(User).where(User.email == email)):
            raise ValueError("email already registered")
        u = User(email=email, hashed_password=hash_password(password), full_name=full_name, is_active=True)
        db.add(u)
        db.commit()
        db.refresh(u)
        return u

    def authenticate(self, db: Session, *, email: str, password: str) -> User | None:
        u = db.scalar(select(User).where(User.email == email))
        if not u or not u.is_active or not verify_password(password, u.hashed_password):
            return None
        return u

    def get(self, db: Session, user_id) -> User | None:
        return db.get(User, user_id)

    def list_users(self, db: Session) -> list[User]:
        return list(db.scalars(select(User).order_by(User.created_at.desc())))

    def assign_role(self, db: Session, user_id, role_name: str) -> User:
        if not is_valid_role(role_name):
            raise ValueError(f"invalid role: {role_name}")
        u = db.get(User, user_id)
        if not u:
            raise ValueError("user not found")
        r = db.scalar(select(Role).where(Role.name == role_name))
        if not r:
            raise ValueError("role not found")
        if r not in u.roles:
            u.roles.append(r)
            db.commit()
            db.refresh(u)
        return u

    def revoke_role(self, db: Session, user_id, role_name: str) -> User:
        u = db.get(User, user_id)
        if not u:
            raise ValueError("user not found")
        u.roles = [r for r in u.roles if r.name != role_name]
        db.commit()
        db.refresh(u)
        return u
