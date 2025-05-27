import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from main import app
from app.core.db import engine, Base
import asyncio


client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    # Create tables
    asyncio.run(Base.metadata.create_all(bind=engine))
    yield
    # Drop tables after tests
    asyncio.run(Base.metadata.drop_all(bind=engine))


@pytest.fixture(scope="function")
def db_session():
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = Session()
    yield session
    asyncio.run(session.close())


def test_register_and_login_success(create_test_db):
    username = "testuser"
    password = "testpass"
    # Register
    r = client.post("/register", data={"username": username, "password": password})
    assert r.status_code == 200
    # Login
    login_response = client.post(
        "/login", data={"username": username, "password": password}
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()


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
    login_response = client.post(
        "/login", data={"username": username, "password": "wrongpass"}
    )
    assert login_response.status_code == 401


def test_login_nonexistent_user(create_test_db):
    login_response = client.post(
        "/login", data={"username": "nope", "password": "nope"}
    )
    assert login_response.status_code == 401
