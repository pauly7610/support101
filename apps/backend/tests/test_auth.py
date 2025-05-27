import pytest
import time

@pytest.mark.asyncio
async def test_login_success(async_client):
    response = await async_client.post("/login", data={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_login_invalid(async_client):
    response = await async_client.post("/login", data={"username": "admin", "password": "wrong"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_protected_route(async_client):
    login = await async_client.post("/login", data={"username": "admin", "password": "admin"})
    token = login.json()["access_token"]
    response = await async_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "message" in response.json()

@pytest.mark.asyncio
async def test_protected_route_no_token(async_client):
    response = await async_client.get("/protected")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_cached_example(async_client):
    t0 = time.time()
    response1 = await async_client.get("/cached-example")
    t1 = time.time()
    response2 = await async_client.get("/cached-example")
    t2 = time.time()
    assert response1.status_code == 200
    assert response2.status_code == 200
    # First response should take longer than second (cached)
    assert (t1 - t0) > 1.5
    assert (t2 - t1) < 0.5
    assert (t1 - t0) > 1.5
    assert (t2 - t1) < 0.5
