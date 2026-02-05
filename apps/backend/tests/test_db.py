import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

import apps.backend.db as db


@pytest.mark.asyncio
async def test_get_engine_returns_engine_instance():
    engine = db.get_engine()
    # Check that engine is an AsyncEngine instance
    from sqlalchemy.ext.asyncio import AsyncEngine

    assert isinstance(engine, AsyncEngine)


def test_get_session_returns_async_session():
    session = db.get_session()
    assert isinstance(session, AsyncSession)


def test_get_base_returns_declarative_base():
    base = db.get_base()
    assert isinstance(base, declarative_base().__class__)


def test_escalation_model_fields():
    escalation = db.Escalation()
    assert hasattr(escalation, "id")
    assert hasattr(escalation, "user_id")
    assert hasattr(escalation, "text")
    assert hasattr(escalation, "timestamp")
    assert hasattr(escalation, "last_updated")
    assert hasattr(escalation, "confidence")
    assert hasattr(escalation, "source_url")


@pytest.mark.asyncio
async def test_init_db_creates_tables(monkeypatch):
    class DummyConn:
        async def run_sync(self, fn):
            # Simulate table creation
            return True

    class DummyAsyncContextManager:
        def __init__(self, conn):
            self._conn = conn

        async def __aenter__(self):
            return self._conn

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return False

    class DummyEngine:
        def begin(self):
            # begin() returns an async context manager, not a coroutine
            return DummyAsyncContextManager(DummyConn())

    monkeypatch.setattr(db, "engine", DummyEngine())
    # Should not raise
    await db.init_db()
