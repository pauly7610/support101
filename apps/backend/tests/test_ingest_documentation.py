from fastapi.testclient import TestClient

from apps.backend.main import app

client = TestClient(app)


def test_invalid_file_type():
    resp = client.post(
        "/ingest_documentation",
        files={"file": ("test.exe", b"fake", "application/octet-stream")},
        data={"chunk_size": 1000},
    )
    assert resp.status_code == 400


def test_invalid_chunk_size():
    with open(__file__, "rb") as f:
        resp = client.post(
            "/ingest_documentation",
            files={"file": ("test.txt", f, "text/plain")},
            data={"chunk_size": 99999},
        )
        assert resp.status_code == 400
