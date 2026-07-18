"""Tests for the agent framework.

Uses an in-memory SQLite database so tests never touch Supabase. All
persistence-backed components (memory, queue, bus, history, metrics,
health) are exercised against real SQLAlchemy sessions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models import models  # noqa: F401  — ensure all tables are registered


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def agent_row(db):
    row = models.Agent(name="test_agent", type="test", status="idle", config={})
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
