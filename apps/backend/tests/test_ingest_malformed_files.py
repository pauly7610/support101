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


def test_malformed_pdf_ingestion():
    """Test ingestion of a malformed/corrupt PDF file."""
    corrupt_pdf = b"%PDF-2.0 invalid_header"
    resp = client.post(
        "/ingest_documentation",
        files={"file": ("corrupt.pdf", corrupt_pdf, "application/pdf")},
        data={"chunk_size": 1024},
    )
    # Should reject malformed PDF or return error
    assert resp.status_code in {400, 422, 500}
