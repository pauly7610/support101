import pytest
from fastapi.testclient import TestClient
from apps.backend.main import app

client = TestClient(app)

def test_ingest_and_query_flow(monkeypatch):
    # Simulate a TXT upload and then a query
    file_content = b"Test document for ingestion."
    response = client.post(
        "/ingest_documentation",
        files={"file": ("test.txt", file_content, "text/plain")},
        data={"chunk_size": 512}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Simulate a generate_reply call
    ticket = {"user_query": "What is ingestion?"}
    response = client.post("/generate_reply", json=ticket)
    assert response.status_code in (200, 504)  # 504 if LLM times out
