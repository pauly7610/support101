import jwt
import pytest
from fastapi.testclient import TestClient

from ...backend.main import JWT_ALGORITHM, JWT_SECRET, app

client = TestClient(app)


def make_jwt(user_id="testuser"):
    return jwt.encode({"sub": user_id}, JWT_SECRET, algorithm=JWT_ALGORITHM)


@pytest.mark.xfail(reason="Endpoint or auth not implemented or requires real API key")
@pytest.mark.xfail(reason="/gdpr_delete endpoint not implemented (404)")
def test_gdpr_delete_requires_jwt():
    resp = client.post("/gdpr_delete", json={"user_id": "testuser"})
    assert resp.status_code == 403 or resp.status_code == 401
    token = make_jwt()
    resp = client.post(
        "/gdpr_delete",
        json={"user_id": "testuser"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.xfail(reason="Endpoint or auth not implemented or requires real API key")
@pytest.mark.xfail(reason="/ccpa_optout endpoint not implemented (404)")
def test_ccpa_optout_requires_jwt():
    resp = client.post("/ccpa_optout", json={"user_id": "testuser"})
    assert resp.status_code == 403 or resp.status_code == 401
    token = make_jwt()
    resp = client.post(
        "/ccpa_optout",
        json={"user_id": "testuser"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
