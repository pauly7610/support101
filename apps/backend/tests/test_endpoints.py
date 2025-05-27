import time

import pytest


@pytest.mark.asyncio
async def get_token(async_client):
    username = "protecteduser"
    password = "protectedpass"
    # Register the user
    await async_client.post("/register", data={"username": username, "password": password})
    # Login to get token
    r = await async_client.post("/login", data={"username": username, "password": password})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_protected_endpoint(async_client):
    token = await get_token(async_client)
    r = await async_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "message" in r.json()


@pytest.mark.asyncio
async def test_protected_endpoint_no_token(async_client):
    r = await async_client.get("/protected")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_cached_example(async_client):
    t0 = time.time()
    r1 = await async_client.get("/cached-example")
    t1 = time.time()
    r2 = await async_client.get("/cached-example")
    t2 = time.time()
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert (t1 - t0) > 1.5  # First call is slow
    assert (t2 - t1) < 0.5  # Second call is fast (cached)
