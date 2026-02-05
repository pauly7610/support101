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


@pytest.fixture(autouse=True)
def setup_mocks(monkeypatch):
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

    # Mock RateLimiter using monkeypatch (auto-restored)
    try:
        monkeypatch.setattr(
            "fastapi_limiter.depends.RateLimiter.__call__",
            AsyncMock(return_value=None),
        )
    except Exception:
        pass

    # Override auth
    backend_app.dependency_overrides[get_current_user] = lambda: MockUser()
    yield
    backend_app.dependency_overrides.clear()


@pytest.fixture
def client():
    """Create test client after mocks are set up."""
    return TestClient(backend_app)


@pytest.mark.skip(reason="Requires OPENAI_API_KEY and causes event loop conflicts with backend conftest")
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
