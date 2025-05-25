import pytest
from fastapi.testclient import TestClient
from apps.backend.main import app, JWT_SECRET, JWT_ALGORITHM
import jwt

client = TestClient(app)

def make_jwt(user_id="testuser"):
    return jwt.encode({"sub": user_id}, JWT_SECRET, algorithm=JWT_ALGORITHM)

def test_gdpr_delete_requires_jwt():
    resp = client.post("/gdpr_delete", json={"user_id": "testuser"})
    assert resp.status_code == 403 or resp.status_code == 401
    token = make_jwt()
    resp = client.post("/gdpr_delete", json={"user_id": "testuser"}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

def test_ccpa_optout_requires_jwt():
    resp = client.post("/ccpa_optout", json={"user_id": "testuser"})
    assert resp.status_code == 403 or resp.status_code == 401
    token = make_jwt()
    resp = client.post("/ccpa_optout", json={"user_id": "testuser"}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
