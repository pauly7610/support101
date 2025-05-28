import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.core import db as db_module


@pytest.mark.asyncio
async def test_get_db_yields_session():
    gen = db_module.get_db()
    session = await gen.__anext__()
    assert isinstance(session, AsyncSession)
    await gen.aclose()


@pytest.mark.asyncio
async def test_get_db_multiple_sessions():
    sessions = []
    for _ in range(3):
        gen = db_module.get_db()
        session = await gen.__anext__()
        assert isinstance(session, AsyncSession)
        sessions.append(session)
        await gen.aclose()


@pytest.mark.asyncio
async def test_get_db_error(monkeypatch):
    monkeypatch.setattr(db_module, "SessionLocal", lambda: (_ for _ in ()).throw(Exception("fail")))
    gen = db_module.get_db()
    with pytest.raises(Exception):
        await gen.__anext__()


def test_engine_and_base():
    assert db_module.engine is not None
    assert db_module.Base is not None
    assert db_module.SessionLocal is not None
    assert db_module.AsyncSession is not None


def test_database_url_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:5432/other")
    import importlib
    import sys

    if "apps.backend.app.core.db" in sys.modules:
        del sys.modules["apps.backend.app.core.db"]
    db_mod = importlib.import_module("apps.backend.app.core.db")
    assert db_mod.engine is not None
    assert os.environ["DATABASE_URL"] == "postgresql+asyncpg://test:5432/other"
