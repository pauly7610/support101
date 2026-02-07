import asyncio
import contextlib
import hashlib
import os
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis import asyncio as redis_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from apps.backend.app.auth.models import User
from apps.backend.app.core.cache import init_redis
from apps.backend.app.core.db import Base
from apps.backend.main import app as fastapi_app
from apps.backend.main import get_db

# Use environment variable or default to test database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/support101_test",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

engine = create_async_engine(DATABASE_URL, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def clear_redis_cache():
    try:
        redis = redis_asyncio.from_url(REDIS_URL, decode_responses=True)
        await redis.flushdb()
        yield
        await redis.close()
    except Exception:
        # Redis not available, skip cache clearing
        yield


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    try:
        if init_redis:
            await init_redis()
    except Exception:
        pass
    yield
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session():
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def async_client():
    # Override FastAPI dependency — create a fresh session per request
    async def override_get_db():
        async with AsyncSessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_externals(monkeypatch):
    # Mock FastAPILimiter to avoid "You must call FastAPILimiter.init" errors
    try:
        from fastapi_limiter import FastAPILimiter

        FastAPILimiter.redis = AsyncMock()
        FastAPILimiter.lua_sha = "mock_sha"
        FastAPILimiter.identifier = AsyncMock(return_value="test_identifier")
        FastAPILimiter.http_callback = AsyncMock()
    except Exception:
        pass

    # Mock RateLimiter dependency to always pass
    with contextlib.suppress(Exception):
        monkeypatch.setattr(
            "fastapi_limiter.depends.RateLimiter.__call__",
            AsyncMock(return_value=None),
        )

    with contextlib.suppress(Exception):
        monkeypatch.setattr("pinecone.Index.query", lambda *args, **kwargs: {"matches": []})
    with contextlib.suppress(Exception):
        monkeypatch.setattr("firecrawl.FirecrawlApp.scrape", lambda *args, **kwargs: None)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_admin_user(setup_database):
    """Insert admin user with username 'admin' and password 'admin' (sha256-hashed) into test DB."""
    try:
        async with engine.begin() as conn:
            hashed_password = hashlib.sha256(b"admin").hexdigest()
            await conn.execute(
                User.__table__.insert().values(username="admin", hashed_password=hashed_password)
            )
    except Exception:
        pass  # Admin user may already exist
