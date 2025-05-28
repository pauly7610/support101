import time

import pytest


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
async def test_protected_route_expired_token(async_client, monkeypatch):
    import datetime

    import jwt

    from apps.backend.app.auth.jwt import ALGORITHM, SECRET_KEY

    expired = jwt.encode(
        {"sub": "admin", "exp": datetime.datetime.utcnow() - datetime.timedelta(seconds=1)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    response = await async_client.get("/protected", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_malformed_token(async_client):
    response = await async_client.get("/protected", headers={"Authorization": "Bearer not.a.jwt"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_user_not_found(async_client, monkeypatch):
    # Patch user lookup to always return None
    async def no_user(*a, **kw):
        from fastapi import HTTPException

        raise HTTPException(status_code=404)

    monkeypatch.setattr("apps.backend.app.auth.jwt.get_current_user", no_user)
    login = await async_client.post("/login", data={"username": "admin", "password": "admin"})
    token = login.json()["access_token"]
    response = await async_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_protected_route_permission_denied(async_client, monkeypatch):
    # Patch user to not be admin
    class DummyUser:
        is_admin = False

    async def dummy_user(*a, **kw):
        return DummyUser()

    monkeypatch.setattr("apps.backend.app.auth.jwt.get_current_user", dummy_user)
    login = await async_client.post("/login", data={"username": "admin", "password": "admin"})
    token = login.json()["access_token"]
    response = await async_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_cached_example_cache_error(async_client, monkeypatch):
    # Simulate cache backend error
    monkeypatch.setattr(
        "apps.backend.app.core.cache.get_cache",
        lambda: (_ for _ in ()).throw(Exception("cache fail")),
    )
    response = await async_client.get("/cached-example")
    assert response.status_code in (500, 503)


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
