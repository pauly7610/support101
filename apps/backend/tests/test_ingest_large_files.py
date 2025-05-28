from fastapi.testclient import TestClient

from ...backend.main import app

client = TestClient(app)


def test_large_pdf_ingestion():
    """Test ingestion of a large (300MB) PDF file."""
    large_pdf = b"%PDF-1.4" + b"0" * (300 * 1024 * 1024)  # 300MB
    resp = client.post(
        "/ingest_documentation",
        files={"file": ("large.pdf", large_pdf, "application/pdf")},
        data={"chunk_size": 1024},
    )
    # Accept either 200 (success) or 413 (payload too large)
    assert resp.status_code in {200, 413}
    if resp.status_code == 200:
        assert resp.json().get("success") is True
