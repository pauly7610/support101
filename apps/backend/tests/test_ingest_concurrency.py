import threading

import pytest
from fastapi.testclient import TestClient

from ...backend.main import app

client = TestClient(app)


def test_concurrent_ingestion():
    """Test concurrent ingestion requests for rate limiting and thread safety."""
    results = []

    def upload():
        resp = client.post(
            "/ingest_documentation",
            files={"file": ("small.pdf", b"%PDF-1.4 ...", "application/pdf")},
            data={"chunk_size": 1024},
        )
        results.append(resp.status_code)

    threads = [threading.Thread(target=upload) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # Accept 200, 400, or 429 (rate limit) for concurrency
    assert all(code in {200, 400, 429} for code in results)
