import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from apps.backend.main import app as backend_app


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable",
)
def test_api_key_masking_in_error():
    client = TestClient(backend_app)
    # Simulate Pinecone error with API key in message
    with patch(
        "packages.llm_engine.vector_store.get_pinecone_index",
        side_effect=Exception("PINECONE_API_KEY=secret-key"),
    ):
        resp = client.post(
            "/generate_reply",
            json={"user_query": "trigger error"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "***" in str(data), "API key should be masked in error response"
        assert data.get("retryable") is True
        assert data.get("documentation", "").endswith("E500")


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable",
)
@pytest.mark.asyncio
async def test_rate_limiting_on_generate_reply(async_client):
    # Simulate burst of requests to /generate_reply
    rate_limited = False
    for _ in range(15):
        resp = await async_client.post("/generate_reply", json={"user_query": "test"})
        if resp.status_code == 429:
            rate_limited = True
            break
    assert rate_limited, "Expected at least one 429 Too Many Requests response on /generate_reply."
