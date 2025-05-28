import asyncio
import sys
from unittest.mock import patch

import app.main as backend_app
import pytest
from httpx import AsyncClient

sys.modules["langchain_openai"] = __import__("types")  # Patch for CI if needed

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
def client():
    return AsyncClient(app=backend_app.app, base_url="http://testserver")


async def test_document_ingestion_and_rag_flow(client):
    # 1. Ingest a sample document
    doc_content = "Refunds are processed within 3 business days."
    files = {"file": ("refunds.txt", doc_content, "text/plain")}
    data = {"chunk_size": 512}
    resp = await client.post("/ingest_documentation", files=files, data=data)
    assert resp.status_code == 200
    assert resp.json().get("ingested", 0) >= 1

    # 2. Query the RAG endpoint for a related question
    payload = {"user_query": "How long do refunds take?"}
    resp = await client.post("/generate_reply", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "reply" in body
    # Should cite the ingested document
    assert body.get("citations") and any(
        "refunds.txt" in c.get("excerpt", "") for c in body["citations"]
    )


async def test_rag_flow_no_citations(client):
    payload = {"user_query": "What is the meaning of life?"}
    resp = await client.post("/generate_reply", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "reply" in body
    # Should not have citations for unrelated question
    assert body.get("citations") == []


async def test_rag_flow_error_handling(client):
    # Simulate LLM timeout or error
    with patch(
        "packages.llm_engine.chains.rag_chain.ChatOpenAI.ainvoke",
        side_effect=asyncio.TimeoutError(),
    ):
        payload = {"user_query": "Trigger timeout"}
        resp = await client.post("/generate_reply", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("error_type") == "llm_timeout"
        assert body.get("retryable") is True
        assert body.get("documentation", "").endswith("E429")


async def test_rag_flow_load(client):
    # Simulate 100 concurrent requests
    async def make_query():
        payload = {"user_query": "How long do refunds take?"}
        r = await client.post("/generate_reply", json=payload)
        assert r.status_code == 200
        return r.json()

    results = await asyncio.gather(*[make_query() for _ in range(100)])
    assert all("reply" in r for r in results)
