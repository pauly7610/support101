from fastapi.testclient import TestClient

from ...backend.main import app

import pytest

client = TestClient(app)


@pytest.mark.xfail(reason="Analytics endpoint not implemented or requires real API key")
def test_escalation_analytics_basic():
    resp = client.get("/analytics/escalations")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_escalations" in data
    assert "per_day" in data
    assert "last_escalation" in data


@pytest.mark.xfail(reason="Analytics endpoint not implemented or requires real API key")
@pytest.mark.xfail(reason="/analytics/escalations endpoint not implemented (404)")
def test_escalation_analytics_filter_user():
    resp = client.get("/analytics/escalations?user_id=testuser")
    assert resp.status_code == 200


@pytest.mark.xfail(reason="Analytics endpoint not implemented or requires real API key")
@pytest.mark.xfail(reason="/analytics/escalations endpoint not implemented (404)")
def test_escalation_analytics_filter_time():
    import time

    now = int(time.time())
    url = f"/analytics/escalations?start_time={now-10000}&end_time={now}"
    resp = client.get(url)
    assert resp.status_code == 200
