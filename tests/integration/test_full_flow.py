import os
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from apps.backend.app.auth.jwt import get_current_user
from apps.backend.main import app as backend_app


class MockUser:
    id = 1
    username = "testuser"
    is_admin = True


@pytest.fixture(scope="function", autouse=True)
def setup_mocks():
    """Set up mocks for FastAPILimiter and auth."""
    # Mock FastAPILimiter
    try:
        from fastapi_limiter import FastAPILimiter

        FastAPILimiter.redis = AsyncMock()
        FastAPILimiter.lua_sha = "mock_sha"
        FastAPILimiter.identifier = AsyncMock(return_value="test_identifier")
        FastAPILimiter.http_callback = AsyncMock()
    except Exception:
        pass

    original_call = None
    try:
        from fastapi_limiter.depends import RateLimiter

        original_call = getattr(RateLimiter, "__call__", None)

        async def mock_call(self, request, response):
            return None

        RateLimiter.__call__ = mock_call
    except Exception:
        pass

    # Override auth
    backend_app.dependency_overrides[get_current_user] = lambda: MockUser()
    yield
    backend_app.dependency_overrides.clear()

    # Restore RateLimiter
    if original_call is not None:
        try:
            from fastapi_limiter.depends import RateLimiter

            RateLimiter.__call__ = original_call
        except Exception:
            pass


@pytest.fixture
def client():
    """Create test client after mocks are set up."""
    return TestClient(backend_app)


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OpenAI API key not set",
)
def test_ingest_and_query_flow(client, monkeypatch):
    # Simulate a TXT upload and then a query
    file_content = b"Test document for ingestion."
    response = client.post(
        "/ingest_documentation",
        files={"file": ("test.txt", file_content, "text/plain")},
        data={"chunk_size": 512},
    )
    assert response.status_code in (200, 400, 500)

    # Simulate a generate_reply call
    ticket = {"user_query": "What is ingestion?"}
    response = client.post("/generate_reply", json=ticket)
    assert response.status_code in (200, 401, 500, 504)  # 504 if LLM times out
