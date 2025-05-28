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


@pytest.mark.asyncio
async def test_protected_endpoint_expired_token(async_client):
    import datetime

    import jwt

    from apps.backend.app.auth.jwt import ALGORITHM, SECRET_KEY

    expired = jwt.encode(
        {"sub": "protecteduser", "exp": datetime.datetime.utcnow() - datetime.timedelta(seconds=1)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    r = await async_client.get("/protected", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_malformed_token(async_client):
    r = await async_client.get("/protected", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_permission_denied(async_client, monkeypatch):
    class DummyUser:
        is_admin = False

    async def dummy_user(*a, **kw):
        return DummyUser()

    monkeypatch.setattr("apps.backend.app.auth.jwt.get_current_user", dummy_user)
    token = await get_token(async_client)
    r = await async_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_endpoint_not_found(async_client):
    r = await async_client.get("/notfound")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cached_example_cache_error(async_client, monkeypatch):
    monkeypatch.setattr(
        "apps.backend.app.core.cache.get_cache",
        lambda: (_ for _ in ()).throw(Exception("cache fail")),
    )
    r = await async_client.get("/cached-example")
    assert r.status_code in (500, 503)
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
