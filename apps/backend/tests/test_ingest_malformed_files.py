from fastapi.testclient import TestClient

from apps.backend.main import app as backend_app

client = TestClient(backend_app)


def test_malformed_pdf_ingestion():
    """Test ingestion of a malformed/corrupt PDF file."""
    corrupt_pdf = b"%PDF-2.0 invalid_header"
    resp = client.post(
        "/ingest_documentation",
        files={"file": ("corrupt.pdf", corrupt_pdf, "application/pdf")},
        data={"chunk_size": 1024},
    )
    # Should reject malformed PDF
    assert resp.status_code in {400, 422}
