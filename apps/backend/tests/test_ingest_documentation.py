from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.backend.main import app as backend_app

client = TestClient(backend_app)


def always_user(*args, **kwargs):
    return {"id": 1, "username": "testuser"}


def test_invalid_file_type():
    """Test that ingestion rejects an invalid file type (e.g., .exe)."""
    with patch("apps.backend.main.get_current_user", always_user):
        resp = client.post(
            "/ingest_documentation",
            files={"file": ("test.exe", b"fake", "application/octet-stream")},
            data={"chunk_size": 1000},
            headers={"Authorization": "Bearer testtoken"},
        )
        assert resp.status_code == 400


def test_valid_pdf_ingestion():
    with patch("apps.backend.main.get_current_user", always_user):
        resp = client.post(
            "/ingest_documentation",
            files={"file": ("test.pdf", b"%PDF-1.4 ...", "application/pdf")},
            data={"chunk_size": 512},
            headers={"Authorization": "Bearer testtoken"},
        )
        assert resp.status_code in (200, 400)


def test_valid_txt_ingestion():
    with patch("apps.backend.main.get_current_user", always_user):
        resp = client.post(
            "/ingest_documentation",
            files={"file": ("test.txt", b"hello world", "text/plain")},
            data={"chunk_size": 512},
            headers={"Authorization": "Bearer testtoken"},
        )
        assert resp.status_code in (200, 400)


def test_valid_md_ingestion():
    with patch("apps.backend.main.get_current_user", always_user):
        resp = client.post(
            "/ingest_documentation",
            files={"file": ("test.md", b"# Title", "text/markdown")},
            data={"chunk_size": 512},
            headers={"Authorization": "Bearer testtoken"},
        )
        assert resp.status_code in (200, 400)


def test_missing_file():
    with patch("apps.backend.main.get_current_user", always_user):
        resp = client.post(
            "/ingest_documentation",
            data={"chunk_size": 512},
            headers={"Authorization": "Bearer testtoken"},
        )
        assert resp.status_code in (400, 422)


def test_missing_chunk_size():
    with patch("apps.backend.main.get_current_user", always_user):
        resp = client.post(
            "/ingest_documentation",
            files={"file": ("test.pdf", b"%PDF-1.4 ...", "application/pdf")},
            headers={"Authorization": "Bearer testtoken"},
        )
        assert resp.status_code in (400, 422)


def test_rate_limit():
    results = []
    with patch("apps.backend.main.get_current_user", always_user):
        for _ in range(11):
            resp = client.post(
                "/ingest_documentation",
                files={"file": ("test.pdf", b"%PDF-1.4 ...", "application/pdf")},
                data={"chunk_size": 512},
                headers={"Authorization": "Bearer testtoken"},
            )
            results.append(resp.status_code)
    assert any(code == 429 for code in results)


def test_ingest_db_error():
    with patch("apps.backend.main.get_current_user", always_user):
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
    with patch("apps.backend.main.get_current_user", always_user):
        with open(__file__, "rb") as f:
            resp = client.post(
                "/ingest_documentation",
                files={"file": ("test.pdf", f.read(), "application/pdf")},
                data={"chunk_size": 999999},
                headers={"Authorization": "Bearer testtoken"},
            )
        assert resp.status_code == 400
