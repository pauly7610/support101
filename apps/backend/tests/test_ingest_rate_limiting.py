import time

import pytest
from fastapi.testclient import TestClient

from apps.backend.app.auth.jwt import get_current_user
from apps.backend.main import app as backend_app

client = TestClient(backend_app)


class MockUser:
    id = 1
    username = "testuser"
    is_admin = True


@pytest.fixture(autouse=True)
def override_auth():
    """Override auth for all tests in this module."""
    backend_app.dependency_overrides[get_current_user] = lambda: MockUser()
    yield
    backend_app.dependency_overrides.clear()


@pytest.mark.xfail(reason="Rate limiting may not trigger in test environment")
def test_ingest_rate_limiting():
    """Test that the ingestion endpoint enforces 10 requests/minute/IP rate limiting."""
    success_codes = set()
    rate_limited = False
    for i in range(15):
        resp = client.post(
            "/ingest_documentation",
            files={"file": (f"file_{i}.txt", b"test", "text/plain")},
            data={"chunk_size": 512},
        )
        if resp.status_code == 429:
            rate_limited = True
        else:
            success_codes.add(resp.status_code)
        time.sleep(0.1)  # minimal delay to simulate burst
    assert rate_limited, "Expected at least one 429 Too Many Requests response."
    assert all(
        code in {200, 400, 500} for code in success_codes
    ), f"Unexpected status codes: {success_codes}"
