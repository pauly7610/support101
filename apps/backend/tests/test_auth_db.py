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
    assert "access_token" in login_response.json()


@pytest.mark.asyncio
async def test_login_wrong_password(async_client):
    username = "testuser2"
    password = "testpass2"
    await async_client.post("/register", data={"username": username, "password": password})
    r = await async_client.post("/login", data={"username": username, "password": "wrong"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(async_client):
    r = await async_client.post("/login", data={"username": "ghost", "password": "ghostpass"})
    assert r.status_code == 401


def test_register_duplicate(create_test_db):
    username = "dupeuser"
    password = "dupepass"
    r1 = client.post("/register", data={"username": username, "password": password})
    assert r1.status_code == 200
    r2 = client.post("/register", data={"username": username, "password": password})
    assert r2.status_code == 400


def test_login_wrong_password(create_test_db):
    username = "baduser"
    password = "goodpass"
    client.post("/register", data={"username": username, "password": password})
    login_response = client.post("/login", data={"username": username, "password": "wrongpass"})
    assert login_response.status_code == 401


def test_login_nonexistent_user(create_test_db):
    login_response = client.post("/login", data={"username": "nope", "password": "nope"})
    assert login_response.status_code == 401
