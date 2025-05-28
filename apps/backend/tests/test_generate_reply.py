import asyncio
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from apps.backend.main import app as backend_app

client = TestClient(backend_app)


@pytest.mark.xfail(reason="LLM API key not set or endpoint not mocked")
@pytest.mark.xfail(reason="OpenAI API key not set or endpoint not mocked")
def test_generate_reply_mock():
    payload = {
        "user_id": "testuser",
        "ticket": {
            "subject": "Test",
            "body": "What is your refund policy?",
            "context": "",
        },
        "history": [],
    }
    resp = client.post("/generate_reply", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert "sources" in data


def test_generate_reply_missing_payload():
    resp = client.post("/generate_reply", json={})
    assert resp.status_code in (400, 422)


def test_generate_reply_invalid_payload():
    resp = client.post("/generate_reply", data="notjson")
    assert resp.status_code in (400, 422)


def test_generate_reply_llm_timeout():
    payload = {
        "user_id": "testuser",
        "ticket": {"subject": "Test", "body": "Timeout?", "context": ""},
        "history": [],
    }
    with patch(
        "packages.llm_engine.chains.rag_chain.ChatOpenAI.ainvoke",
        side_effect=asyncio.TimeoutError(),
    ):
        resp = client.post("/generate_reply", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("error_type") == "llm_timeout"
        assert data.get("retryable") is True


def test_generate_reply_vector_store_error():
    payload = {
        "user_id": "testuser",
        "ticket": {"subject": "Test", "body": "Vector fail", "context": ""},
        "history": [],
    }
    with patch(
        "packages.llm_engine.chains.rag_chain.RAGChain._safe_query_pinecone",
        side_effect=Exception("fail"),
    ):
        resp = client.post("/generate_reply", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("error_type") == "vector_store_error"
        assert data.get("retryable") is True


def test_generate_reply_citation_filtering():
    payload = {
        "user_id": "testuser",
        "ticket": {"subject": "Test", "body": "Cite test", "context": ""},
        "history": [],
    }
    fake_citations = [
        {
            "score": 0.8,
            "metadata": {
                "source_url": "url1",
                "text": "Doc1",
                "last_updated": "2025-01-01",
            },
        },
        {
            "score": 0.6,
            "metadata": {
                "source_url": "url2",
                "text": "Doc2",
                "last_updated": "2025-01-01",
            },
        },
    ]
    with patch(
        "packages.llm_engine.chains.rag_chain.RAGChain._safe_query_pinecone",
        return_value=fake_citations,
    ):
        with patch(
            "packages.llm_engine.chains.rag_chain.ChatOpenAI.ainvoke",
            return_value="Answer.",
        ):
            resp = client.post("/generate_reply", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert "reply" in data
            assert "citations" in data
            assert any(c.get("confidence", 0) >= 0.75 for c in data.get("citations", []))
