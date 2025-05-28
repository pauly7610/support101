from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from apps.backend.app.compliance.router import router

app = FastAPI()
app.include_router(router)


class DummyUser:
    def __init__(self, is_admin=True):
        self.is_admin = is_admin


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


def test_gdpr_delete_permission_denied(client, non_admin_user):
    with patch("apps.backend.app.compliance.router.get_current_user", return_value=non_admin_user):
        response = client.post("/gdpr_delete", json={"user_id": "u1"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "Insufficient permissions"


def test_gdpr_delete_admin_success(client, admin_user):
    with patch(
        "apps.backend.app.compliance.router.get_current_user", return_value=admin_user
    ), patch("apps.backend.app.compliance.router.get_db", new_callable=AsyncMock) as db_mock:
        db_mock.return_value.execute = AsyncMock()
        db_mock.return_value.commit = AsyncMock()
        response = client.post("/gdpr_delete", json={"user_id": "u2"})
        assert response.status_code == 200
        assert response.json()["status"] == "User data permanently deleted"


def test_gdpr_delete_db_error(client, admin_user):
    with patch(
        "apps.backend.app.compliance.router.get_current_user", return_value=admin_user
    ), patch("apps.backend.app.compliance.router.get_db", new_callable=AsyncMock) as db_mock:
        db_mock.return_value.execute = AsyncMock(side_effect=Exception("DB error"))
        db_mock.return_value.commit = AsyncMock()
        response = client.post("/gdpr_delete", json={"user_id": "u3"})
        assert response.status_code in (500, 503)


def test_ccpa_optout_success(client):
    with patch("apps.backend.app.compliance.router.get_db", new_callable=AsyncMock) as db_mock:
        db_mock.return_value.execute = AsyncMock()
        db_mock.return_value.commit = AsyncMock()
        response = client.post("/ccpa_optout", json={"user_id": "u4"})
        assert response.status_code == 200
        assert response.json()["status"] == "Opt-out preference recorded"


def test_ccpa_optout_db_error(client):
    with patch("apps.backend.app.compliance.router.get_db", new_callable=AsyncMock) as db_mock:
        db_mock.return_value.execute = AsyncMock(side_effect=Exception("DB error"))
        db_mock.return_value.commit = AsyncMock()
        response = client.post("/ccpa_optout", json={"user_id": "u5"})
        assert response.status_code in (500, 503)
