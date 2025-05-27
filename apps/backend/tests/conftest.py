import asyncio
import os

# Force all test code to use the test DB
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/support101_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("OPENAI_API_KEY", "dummy")

import asyncio
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from apps.backend.app.core.db import Base, SessionLocal, engine
from apps.backend.main import app as fastapi_app
from apps.backend.main import get_db

# Use test DB URL
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/support101_test",
)

engine = create_async_engine(TEST_DATABASE_URL, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(setup_database):
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def async_client(async_session):
    # Override FastAPI dependency
    async def override_get_db():
        yield async_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()


# If you use FastAPI cache, import and initialize here
try:
    from apps.backend.app.core.cache import init_redis
except ImportError:
    init_redis = None


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if init_redis:
        await init_redis()
    yield
    # Optionally drop tables after tests for isolation
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)


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


import hashlib

# --- Mock external APIs for test safety ---
import pytest

from apps.backend.app.auth.models import User


@pytest.fixture(autouse=True)
def mock_externals(mocker):
    try:
        mocker.patch("pinecone.Index.query", return_value={"matches": []})
    except Exception:
        pass
    try:
        mocker.patch("firecrawl.FirecrawlApp.scrape")
    except Exception:
        pass


@pytest.fixture(scope="session", autouse=True)
def create_admin_user(setup_test_db):
    """Insert admin user with username 'admin' and password 'admin' (sha256-hashed) into test DB."""

    async def _insert():
        async with engine.begin() as conn:
            hashed_password = hashlib.sha256("admin".encode()).hexdigest()
            await conn.execute(
                User.__table__.insert().values(username="admin", hashed_password=hashed_password)
            )

    asyncio.get_event_loop().run_until_complete(_insert())


@pytest.fixture(scope="function")
def db_session():
    session = SessionLocal()
    yield session
    asyncio.get_event_loop().run_until_complete(session.close())


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
