import uuid

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from apps.backend.app.analytics.router import router
from apps.backend.app.auth.jwt import get_current_user
from apps.backend.app.core.db import get_db

app = FastAPI()
app.include_router(router)


class DummyUser:
    def __init__(self, is_admin=True):
        self.is_admin = is_admin
        self.id = str(uuid.uuid4())


class MockRow:
    """Mock SQLAlchemy row that supports dict() conversion."""

    def __init__(self, data: dict):
        self._mapping = data

    def __iter__(self):
        return iter(self._mapping.items())

    def __getitem__(self, key):
        return self._mapping[key]

    def keys(self):
        return self._mapping.keys()


class MockDBSession:
    """Mock database session that returns dummy results."""

    def __init__(self, dummy_result):
        # Convert list of dicts to list of MockRow objects
        self.dummy_result = [MockRow(r) if isinstance(r, dict) else r for r in dummy_result]

    async def execute(self, sql, params=None):
        class DummyResult:
            def __init__(self, data):
                self._data = data

            def all(self):
                return self._data

            def fetchall(self):
                return self._data

            def fetchone(self):
                return self._data[0] if self._data else None

        return DummyResult(self.dummy_result)


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
    """Create a mock database session."""
    dummy_result = [
        {"total_escalations": 10, "avg_response_time": 5.0, "date": "2024-01-01"},
    ]
    return MockDBSession(dummy_result)


@pytest.mark.parametrize(
    "endpoint,params",
    [
        ("/escalations", {}),
        ("/escalations/by-agent", {}),
        ("/escalations/by-category", {}),
    ],
)
def test_permission_denied(client, non_admin_user, mock_db, endpoint, params):
    app.dependency_overrides = {}
    app.dependency_overrides[get_current_user] = lambda: non_admin_user
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get(endpoint, params=params)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "Insufficient permissions"
    finally:
        app.dependency_overrides = {}


@pytest.mark.parametrize(
    "endpoint", ["/escalations", "/escalations/by-agent", "/escalations/by-category"]
)
def test_admin_access_success(client, admin_user, mock_db, endpoint):
    app.dependency_overrides = {}
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        # Check for actual response keys from each endpoint
        assert "escalations" in data or "by_agent" in data or "by_category" in data
    finally:
        app.dependency_overrides = {}


@pytest.mark.parametrize(
    "endpoint,params",
    [
        (
            "/escalations",
            {"user_id": "u1", "start_time": 1700000000, "end_time": 1700001000},
        ),
        ("/escalations/by-agent", {"agent_id": "a1"}),
        ("/escalations/by-category", {"category": "compliance"}),
    ],
)
def test_query_params(client, admin_user, mock_db, endpoint, params):
    app.dependency_overrides = {}
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get(endpoint, params=params)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "escalations" in data or "by_agent" in data or "by_category" in data
    finally:
        app.dependency_overrides = {}
