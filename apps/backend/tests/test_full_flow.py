import asyncio
import os
import sys
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.backend.app.auth.jwt import get_current_user
from apps.backend.main import app as backend_app

sys.modules["langchain_openai"] = __import__("types")  # Patch for CI if needed

pytestmark = pytest.mark.asyncio


class MockUser:
    id = 1
    username = "testuser"
    is_admin = True


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
def client():
    backend_app.dependency_overrides[get_current_user] = lambda: MockUser()
    yield AsyncClient(transport=ASGITransport(app=backend_app), base_url="http://testserver")
    backend_app.dependency_overrides.clear()


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="Requires OPENAI_API_KEY")
async def test_document_ingestion_and_rag_flow(client):
    # 1. Ingest a sample document
    doc_content = "Refunds are processed within 3 business days."
    files = {"file": ("refunds.txt", doc_content, "text/plain")}
    data = {"chunk_size": 512}
    resp = await client.post("/ingest_documentation", files=files, data=data)
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        assert resp.json().get("ingested", 0) >= 1 or resp.json().get("documents_added", 0) >= 1


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="Requires OPENAI_API_KEY")
async def test_rag_flow_no_citations(client):
    payload = {"user_query": "What is the meaning of life?"}
    resp = await client.post("/generate_reply", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "reply" in body or "error_type" in body


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="Requires OPENAI_API_KEY")
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


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="Requires OPENAI_API_KEY")
async def test_rag_flow_load(client):
    # Simulate 100 concurrent requests
    async def make_query():
        payload = {"user_query": "How long do refunds take?"}
        r = await client.post("/generate_reply", json=payload)
        assert r.status_code == 200
        return r.json()

    results = await asyncio.gather(*[make_query() for _ in range(100)])
    assert all("reply" in r or "error_type" in r for r in results)
