import pytest
from fastapi.testclient import TestClient

from apps.backend.main import app

client = TestClient(app)


def test_generate_reply_mock():
    payload = {
        "user_id": "testuser",
        "ticket": {
            "subject": "Test",
            "body": "What is your refund policy?",
            "context": "",
        },
        "history": [],
    }
    resp = client.post("/generate_reply", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert "sources" in data
