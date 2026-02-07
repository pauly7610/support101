import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from apps.backend.main import app as backend_app

client = TestClient(backend_app)


@pytest.mark.xfail(reason="LLM API key not set or endpoint not mocked")
def test_generate_reply_mock():
    payload = {
        "ticket_id": "test-001",
        "user_id": "testuser",
        "user_query": "What is your refund policy?",
    }
    resp = client.post("/generate_reply", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "reply_text" in data
    assert "sources" in data


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="Requires OPENAI_API_KEY")
def test_generate_reply_missing_payload():
    resp = client.post("/generate_reply", json={})
    assert resp.status_code in (400, 422)


def test_generate_reply_invalid_payload():
    resp = client.post("/generate_reply", data="notjson")
    assert resp.status_code in (400, 422)


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="Requires OPENAI_API_KEY")
def test_generate_reply_llm_timeout():
    payload = {
        "ticket_id": "test-timeout",
        "user_id": "testuser",
        "user_query": "Timeout?",
    }
    with patch(
        "packages.llm_engine.chains.rag_chain.ChatOpenAI.ainvoke",
        side_effect=TimeoutError(),
    ):
        resp = client.post("/generate_reply", json=payload)
        assert resp.status_code in (200, 504)
        data = resp.json()
        assert (
            data.get("error_type") == "llm_timeout"
            or data.get("error", {}).get("error_type") == "llm_timeout"
        )


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="Requires OPENAI_API_KEY")
def test_generate_reply_vector_store_error():
    payload = {
        "ticket_id": "test-vector-err",
        "user_id": "testuser",
        "user_query": "Vector fail",
    }
    with patch(
        "packages.llm_engine.chains.rag_chain.RAGChain._safe_query_pinecone",
        side_effect=Exception("fail"),
    ):
        resp = client.post("/generate_reply", json=payload)
        assert resp.status_code in (200, 500)
        data = resp.json()
        assert "error_type" in data or "error" in data


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="Requires OPENAI_API_KEY")
def test_generate_reply_citation_filtering():
    payload = {
        "ticket_id": "test-cite",
        "user_id": "testuser",
        "user_query": "Cite test",
    }
    fake_citations = [
        {
            "score": 0.8,
            "metadata": {
                "source_url": "https://example.com/doc1",
                "text": "Doc1",
                "last_updated": "2025-01-01",
            },
        },
        {
            "score": 0.6,
            "metadata": {
                "source_url": "https://example.com/doc2",
                "text": "Doc2",
                "last_updated": "2025-01-01",
            },
        },
    ]
    with (
        patch(
            "packages.llm_engine.chains.rag_chain.RAGChain._safe_query_pinecone",
            return_value=fake_citations,
        ),
        patch(
            "packages.llm_engine.chains.rag_chain.ChatOpenAI.ainvoke",
            return_value="Answer.",
        ),
    ):
        resp = client.post("/generate_reply", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "reply_text" in data
        assert "sources" in data
