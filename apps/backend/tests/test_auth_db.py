import pytest


@pytest.mark.asyncio
async def test_register_and_login_success(async_client):
    username = "testuser"
    password = "testpass"
    # Register
    r = await async_client.post("/register", data={"username": username, "password": password})
    assert r.status_code == 200
    # Login
    login_response = await async_client.post(
        "/login", data={"username": username, "password": password}
    )
    assert login_response.status_code == 200


@pytest.mark.asyncio
async def test_register_duplicate(async_client):
    username = "dupeuser"
    password = "dupepass"
    await async_client.post("/register", data={"username": username, "password": password})
    r = await async_client.post("/register", data={"username": username, "password": password})
    assert r.status_code in (400, 409)


@pytest.mark.asyncio
async def test_register_invalid_data(async_client):
    r = await async_client.post("/register", data={"username": "", "password": ""})
    assert r.status_code in (400, 422)


@pytest.mark.asyncio
async def test_register_db_error(async_client, monkeypatch):
    # Simulate DB error on register
    monkeypatch.setattr(
        "apps.backend.app.auth.users.create_user",
        lambda *a, **k: (_ for _ in ()).throw(Exception("db fail")),
    )
    r = await async_client.post("/register", data={"username": "fail", "password": "fail"})
    assert r.status_code in (500, 503)


@pytest.mark.asyncio
async def test_login_db_error(async_client, monkeypatch):
    # Simulate DB error on login
    monkeypatch.setattr(
        "apps.backend.app.auth.users.get_user_by_username",
        lambda *a, **k: (_ for _ in ()).throw(Exception("db fail")),
    )
    r = await async_client.post("/login", data={"username": "fail", "password": "fail"})
    assert r.status_code in (500, 503)


@pytest.mark.asyncio
async def test_login_wrong_password(async_client):
    username = "testuser2"
    password = "testpass2"
    await async_client.post("/register", data={"username": username, "password": password})
    r = await async_client.post("/login", data={"username": username, "password": "wrong"})
    assert r.status_code in (400, 401)


@pytest.mark.asyncio
async def test_login_nonexistent_user(async_client):
    r = await async_client.post("/login", data={"username": "ghost", "password": "ghostpass"})
    assert r.status_code == 401
