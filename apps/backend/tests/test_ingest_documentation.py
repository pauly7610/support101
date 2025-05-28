import pytest
from fastapi.testclient import TestClient

from ...backend.main import app

client = TestClient(app)


from fastapi.testclient import TestClient

from ...backend.main import app

client = TestClient(app)


def test_invalid_file_type():
    """Test that ingestion rejects an invalid file type (e.g., .exe)."""
    resp = client.post(
        "/ingest_documentation",
        files={"file": ("test.exe", b"fake", "application/octet-stream")},
        data={"chunk_size": 1000},
    )
    assert resp.status_code == 400


def test_invalid_chunk_size():
    """Test that ingestion rejects an invalid chunk size."""
    with open(__file__, "rb") as f:
        resp = client.post(
            "/ingest_documentation",
            files={"file": ("test.pdf", f.read(), "application/pdf")},
            data={"chunk_size": 999999},
        )
    assert resp.status_code == 400
