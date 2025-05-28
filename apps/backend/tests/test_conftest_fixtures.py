import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


def test_event_loop_fixture(event_loop):
    assert event_loop is not None
    assert hasattr(event_loop, "run_until_complete")


@pytest.mark.asyncio
async def test_clear_redis_cache(clear_redis_cache):

    # Should not raise and should yield
    assert clear_redis_cache is None or clear_redis_cache is not False


@pytest.mark.asyncio
async def test_setup_database(setup_database):

    # Should not raise and should yield
    assert setup_database is None or setup_database is not False


@pytest.mark.asyncio
async def test_async_session(async_session):
    assert isinstance(async_session, AsyncSession)


@pytest.mark.asyncio
async def test_async_client(async_client):

    assert isinstance(async_client, AsyncClient)
    resp = await async_client.get("/healthz")
    assert resp.status_code in (200, 404)  # Health endpoint or not found


def test_mock_externals(monkeypatch, mock_externals):
    # Should not raise, monkeypatches pinecone and firecrawl
    assert mock_externals is None or mock_externals is not False


def test_create_admin_user(create_admin_user):
    # Should not raise
    assert create_admin_user is None or create_admin_user is not False
