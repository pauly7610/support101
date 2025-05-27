import os
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.db import Base
from main import app
from fastapi.testclient import TestClient

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/support101_test",
)
engine = create_async_engine(TEST_DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(setup())
    yield
    # Optionally drop tables after tests
    # asyncio.get_event_loop().run_until_complete(engine.dispose())


@pytest.fixture(scope="function")
def db_session():
    session = SessionLocal()
    yield session
    asyncio.get_event_loop().run_until_complete(session.close())


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
