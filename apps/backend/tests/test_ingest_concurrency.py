import threading
from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.backend.main import app as backend_app

client = TestClient(backend_app)


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


def test_rate_limit_exceeded():
    results = []
    for _ in range(12):
        resp = client.post(
            "/ingest_documentation",
            files={"file": ("small.pdf", b"%PDF-1.4 ...", "application/pdf")},
            data={"chunk_size": 1024},
        )
        results.append(resp.status_code)
    assert any(code == 429 for code in results)


def test_invalid_file_type():
    resp = client.post(
        "/ingest_documentation",
        files={"file": ("bad.exe", b"MZ...", "application/octet-stream")},
        data={"chunk_size": 1024},
    )
    assert resp.status_code in (400, 415)


def test_invalid_chunk_size():
    resp = client.post(
        "/ingest_documentation",
        files={"file": ("ok.pdf", b"%PDF-1.4 ...", "application/pdf")},
        data={"chunk_size": 9999},
    )
    assert resp.status_code in (400, 422)


def test_ingest_db_error():
    with patch("apps.backend.main.get_db", side_effect=Exception("db fail")):
        resp = client.post(
            "/ingest_documentation",
            files={"file": ("small.pdf", b"%PDF-1.4 ...", "application/pdf")},
            data={"chunk_size": 1024},
        )
        assert resp.status_code in (500, 503)
