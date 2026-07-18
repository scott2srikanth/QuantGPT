"""Shared API dependencies (re-exports for convenience)."""

from __future__ import annotations

from app.auth.dependencies import get_current_user, require_roles
from app.core.container import Container, get_container
from app.db.session import get_db

__all__ = [
    "get_current_user",
    "require_roles",
    "get_container",
    "Container",
    "get_db",
]
