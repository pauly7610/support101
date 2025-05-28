import pytest
import time
from fastapi.testclient import TestClient
from ...backend.main import app

client = TestClient(app)

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
    assert all(code in {200, 400} for code in success_codes), f"Unexpected status codes: {success_codes}"
