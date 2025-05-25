import pytest
from fastapi.testclient import TestClient
from apps.backend.main import app

client = TestClient(app)

def test_escalation_analytics_basic():
    resp = client.get("/analytics/escalations")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_escalations" in data
    assert "per_day" in data
    assert "last_escalation" in data

def test_escalation_analytics_filter_user():
    resp = client.get("/analytics/escalations?user_id=testuser")
    assert resp.status_code == 200

def test_escalation_analytics_filter_time():
    import time
    now = int(time.time())
    resp = client.get(f"/analytics/escalations?start_time={now-10000}&end_time={now}")
    assert resp.status_code == 200
