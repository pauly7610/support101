import jwt
import pytest
from fastapi.testclient import TestClient

from ...backend.main import JWT_ALGORITHM, JWT_SECRET, app

client = TestClient(app)


def make_jwt(user_id="testuser", is_admin=False):
    return jwt.encode({"sub": user_id, "is_admin": is_admin}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def test_gdpr_delete_requires_jwt():
    # No JWT
    resp = client.post("/v1/compliance/gdpr_delete?user_id=testuser")
    assert resp.status_code in (401, 403)
    # Non-admin JWT
    token = make_jwt()
    resp = client.post(
        "/v1/compliance/gdpr_delete?user_id=testuser",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (401, 403)
    # Admin JWT
    token = make_jwt(is_admin=True)
    resp = client.post(
        "/v1/compliance/gdpr_delete?user_id=testuser",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 404, 403)  # 404 if user doesn't exist


def test_ccpa_optout_requires_jwt():
    resp = client.post("/v1/compliance/ccpa_optout?user_id=testuser")
    assert resp.status_code in (401, 403)
    token = make_jwt()
    resp = client.post(
        "/v1/compliance/ccpa_optout?user_id=testuser",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 404)
