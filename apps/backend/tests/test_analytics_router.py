import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from apps.backend.app.analytics.router import router
from apps.backend.app.auth.jwt import get_current_user

app = FastAPI()
app.include_router(router)


class DummyUser:
    def __init__(self, is_admin=True):
        self.is_admin = is_admin
        self.id = str(uuid.uuid4())


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


@pytest.mark.parametrize(
    "endpoint,params",
    [("/escalations", {}), ("/escalations/by-agent", {}), ("/escalations/by-category", {})],
)
def test_permission_denied(client, non_admin_user, endpoint, params):
    app.dependency_overrides = {}
    app.dependency_overrides[get_current_user] = lambda: non_admin_user
    response = client.get(endpoint, params=params)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Insufficient permissions"


@pytest.mark.parametrize(
    "endpoint", ["/escalations", "/escalations/by-agent", "/escalations/by-category"]
)
def test_admin_access_success(client, admin_user, endpoint):
    dummy_result = [(10, 5.0, "2024-01-01")]

    async def dummy_execute(sql, params):
        class Dummy:
            def all(self):
                return dummy_result

        return Dummy()

    app.dependency_overrides = {}
    app.dependency_overrides[get_current_user] = lambda: admin_user
    with patch("apps.backend.app.analytics.router.get_db", new_callable=AsyncMock) as db_mock:
        db_mock.return_value.execute = AsyncMock(side_effect=dummy_execute)
        response = client.get(endpoint)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.parametrize(
    "endpoint,params",
    [
        ("/escalations", {"user_id": "u1", "start_time": 1700000000, "end_time": 1700001000}),
        ("/escalations/agent", {"agent_id": "a1"}),
        ("/escalations/category", {"category": "compliance"}),
    ],
)
def test_query_params(client, admin_user, endpoint, params):
    dummy_result = [(1, 2.0, "2024-01-02")]

    async def dummy_execute(sql, params):

        class Dummy:
            def all(self):
                return dummy_result

        return Dummy()

    with patch(
        "apps.backend.app.analytics.router.get_current_user", return_value=admin_user
    ), patch("apps.backend.app.analytics.router.get_db", new_callable=AsyncMock) as db_mock:
        db_mock.return_value.execute = AsyncMock(side_effect=dummy_execute)
        response = client.get(endpoint, params=params)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
