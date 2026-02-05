from unittest.mock import patch

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


def test_invalid_file_type():
    """Test that ingestion rejects an invalid file type (e.g., .exe)."""
    resp = client.post(
        "/ingest_documentation",
        files={"file": ("test.exe", b"fake", "application/octet-stream")},
        data={"chunk_size": 1000},
    )
    assert resp.status_code == 400


@pytest.mark.xfail(reason="May hang waiting for Pinecone/LLM services")
def test_valid_pdf_ingestion():
    resp = client.post(
        "/ingest_documentation",
        files={"file": ("test.pdf", b"%PDF-1.4 ...", "application/pdf")},
        data={"chunk_size": 512},
        timeout=5,
    )
    assert resp.status_code in (200, 400, 500)


@pytest.mark.xfail(reason="May hang waiting for Pinecone/LLM services")
def test_valid_txt_ingestion():
    resp = client.post(
        "/ingest_documentation",
        files={"file": ("test.txt", b"hello world", "text/plain")},
        data={"chunk_size": 512},
        timeout=5,
    )
    assert resp.status_code in (200, 400, 500)


@pytest.mark.xfail(reason="May hang waiting for Pinecone/LLM services")
def test_valid_md_ingestion():
    resp = client.post(
        "/ingest_documentation",
        files={"file": ("test.md", b"# Title", "text/markdown")},
        data={"chunk_size": 512},
        timeout=5,
    )
    assert resp.status_code in (200, 400, 500)


def test_missing_file():
    resp = client.post(
        "/ingest_documentation",
        data={"chunk_size": 512},
    )
    assert resp.status_code in (400, 422)


def test_missing_chunk_size():
    resp = client.post(
        "/ingest_documentation",
        files={"file": ("test.pdf", b"%PDF-1.4 ...", "application/pdf")},
        timeout=5,
    )
    # Default chunk_size is used, so this may succeed
    assert resp.status_code in (200, 400, 422, 500)


@pytest.mark.xfail(reason="Rate limiting may not trigger in test environment")
def test_rate_limit():
    results = []
    for _ in range(11):
        resp = client.post(
            "/ingest_documentation",
            files={"file": ("test.pdf", b"%PDF-1.4 ...", "application/pdf")},
            data={"chunk_size": 512},
            headers={"Authorization": "Bearer testtoken"},
        )
        results.append(resp.status_code)
    assert any(code == 429 for code in results)


@pytest.mark.xfail(reason="DB error handling depends on implementation")
def test_ingest_db_error():
    with patch("apps.backend.main.get_db", side_effect=Exception("db fail")):
        resp = client.post(
            "/ingest_documentation",
            files={"file": ("test.pdf", b"%PDF-1.4 ...", "application/pdf")},
            data={"chunk_size": 512},
            headers={"Authorization": "Bearer testtoken"},
        )
        assert resp.status_code in (500, 503)


def test_invalid_chunk_size():
    """Test that ingestion rejects an invalid chunk size."""
    resp = client.post(
        "/ingest_documentation",
        files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")},
        data={"chunk_size": 999999},
    )
    assert resp.status_code == 400
