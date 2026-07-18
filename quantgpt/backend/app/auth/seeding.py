from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import roles as rc
from app.auth.passwords import hash_password
from app.config.settings import get_settings
from app.db.session import SessionLocal
from app.logging.config import get_logger
from app.models.models import Role, User

_log = get_logger("app.seeding")


def _get_or_create_role(db: Session, name: str, desc: str) -> Role:
    r = db.scalar(select(Role).where(Role.name == name))
    if r:
        return r
    r = Role(name=name, description=desc)
    db.add(r)
    db.flush()
    return r


def seed_admin_user() -> None:
    s = get_settings()
    db: Session = SessionLocal()
    try:
        for name, desc in [(rc.ADMIN, "Full administrative access"), (rc.TRADER, "Place and manage orders"), (rc.VIEWER, "Read-only access")]:
            _get_or_create_role(db, name, desc)
        existing = db.scalar(select(User).where(User.email == s.quantgpt_admin_email))
        if existing:
            _log.info("seeding.admin_exists", email=s.quantgpt_admin_email)
            return
        admin_role = _get_or_create_role(db, rc.ADMIN, "Full administrative access")
        db.add(User(email=s.quantgpt_admin_email, hashed_password=hash_password(s.quantgpt_admin_password), full_name="QuantGPT Admin", is_active=True, roles=[admin_role]))
        db.commit()
        _log.info("seeding.admin_created", email=s.quantgpt_admin_email)
    finally:
        db.close()
