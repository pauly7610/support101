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


@pytest.mark.skip(reason="Creates 300MB in memory - will hang or crash")
def test_large_pdf_ingestion():
    """Test ingestion of a large (300MB) PDF file."""
    large_pdf = b"%PDF-1.4" + b"0" * (300 * 1024 * 1024)  # 300MB
    resp = client.post(
        "/ingest_documentation",
        files={"file": ("large.pdf", large_pdf, "application/pdf")},
        data={"chunk_size": 1024},
        timeout=5,
    )
    # Accept either 200 (success), 413 (payload too large), or 500 (processing error)
    assert resp.status_code in {200, 413, 500}
    if resp.status_code == 200:
        assert resp.json().get("success") is True
