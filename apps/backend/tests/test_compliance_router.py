import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from apps.backend.app.auth.jwt import get_current_user
from apps.backend.app.compliance.router import router
from apps.backend.app.core.db import get_db

app = FastAPI()
app.include_router(router)


class DummyUser:
    def __init__(self, is_admin=True):
        self.is_admin = is_admin


class MockDBSession:
    """Mock database session for compliance tests."""

    def __init__(self, should_error=False):
        self.should_error = should_error

    async def execute(self, sql, params=None):
        if self.should_error:
            raise Exception("DB error")

        class DummyResult:
            def fetchall(self):
                return []

            def fetchone(self):
                return None

        return DummyResult()

    async def commit(self):
        pass


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_user():
    return DummyUser(is_admin=True)


@pytest.fixture
def non_admin_user():
    return DummyUser(is_admin=False)


@pytest.fixture
def mock_db():
    return MockDBSession(should_error=False)


@pytest.fixture
def mock_db_error():
    return MockDBSession(should_error=True)


def test_gdpr_delete_permission_denied(client, non_admin_user, mock_db):
    app.dependency_overrides = {}
    app.dependency_overrides[get_current_user] = lambda: non_admin_user
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.post("/gdpr_delete", json={"user_id": "u1"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "Insufficient permissions"
    finally:
        app.dependency_overrides = {}


def test_gdpr_delete_admin_success(client, admin_user, mock_db):
    app.dependency_overrides = {}
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.post("/gdpr_delete", json={"user_id": "u2"})
        assert response.status_code == 200
        assert response.json()["status"] == "User data permanently deleted"
    finally:
        app.dependency_overrides = {}


def test_gdpr_delete_db_error(client, admin_user, mock_db_error):
    app.dependency_overrides = {}
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db_error
    try:
        response = client.post("/gdpr_delete", json={"user_id": "u3"})
        assert response.status_code in (500, 503)
    finally:
        app.dependency_overrides = {}


def test_ccpa_optout_success(client, mock_db):
    app.dependency_overrides = {}
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.post("/ccpa_optout", json={"user_id": "u4"})
        assert response.status_code == 200
        assert response.json()["status"] == "Opt-out preference recorded"
    finally:
        app.dependency_overrides = {}


def test_ccpa_optout_db_error(client, mock_db_error):
    app.dependency_overrides = {}
    app.dependency_overrides[get_db] = lambda: mock_db_error
    try:
        response = client.post("/ccpa_optout", json={"user_id": "u5"})
        assert response.status_code in (500, 503)
    finally:
        app.dependency_overrides = {}
