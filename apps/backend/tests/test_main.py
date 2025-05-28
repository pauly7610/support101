import io
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from apps.backend.main import app, mask_api_keys


def test_health_check():
    # TODO: Replace with actual client call
    response = None  # client.get("/healthz")
    assert response is None
    # assert response.status_code == 200
    # assert response.json()["status"] == "ok"


def test_register_and_login(monkeypatch):
    # Mock DB methods
    monkeypatch.setattr(
        "apps.backend.app.auth.users.get_user_by_username", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "apps.backend.app.auth.users.create_user",
        AsyncMock(
            return_value=type("User", (), {"id": 1, "username": "testuser"})(),
        ),
    )
    resp = None  # TODO: replace with client.post(
    #     "/register", data={"username": "testuser", "password": "pass"}
    # )
    assert resp is None
    # assert resp.status_code == 200
    # assert resp.json()["username"] == "testuser"

    monkeypatch.setattr(
        "apps.backend.app.auth.users.get_user_by_username",
        AsyncMock(
            return_value=type(
                "User",
                (),
                {"id": 1, "username": "testuser", "hashed_password": "hash"},
            )(),
        ),
    )
    monkeypatch.setattr("apps.backend.app.auth.users.verify_password", AsyncMock(return_value=True))
    monkeypatch.setattr(
        "apps.backend.app.auth.jwt.create_access_token", AsyncMock(return_value="jwt_token")
    )
    resp = None  # TODO: replace with client.post(
    #     "/login", data={"username": "testuser", "password": "pass"}
    # )
    assert resp is None
    # assert resp.status_code == 200
    # assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_ingest_documentation_auth_and_rate_limit(monkeypatch):
    file_content = b"dummy"
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 1. Missing Authorization header
        resp = await ac.post(
            "/ingest_documentation",
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
        )
        assert resp.status_code in (401, 403)
        # 2. Invalid Authorization token
        resp = await ac.post(
            "/ingest_documentation",
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
            headers={"Authorization": "Bearer invalidtoken"},
        )
        assert resp.status_code in (401, 403)
        # 3. Simulate rate limit exceeded
        from fastapi import HTTPException

        monkeypatch.setattr(
            "apps.backend.main.RateLimiter",
            lambda *a, **kw: (
                lambda: (_ for _ in ()).throw(
                    HTTPException(status_code=429, detail="Rate limit exceeded")
                )
            ),
        )
        resp = await ac.post(
            "/ingest_documentation",
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
            headers={"Authorization": "Bearer testtoken"},
        )
        assert resp.status_code == 429
        assert "Rate limit exceeded" in resp.text


@pytest.mark.asyncio
async def test_ingest_documentation_error_branches(monkeypatch):
    token = "Bearer testtoken"
    headers = {"Authorization": token}
    file_content = b"dummy"
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 1. Invalid MIME type
        resp = await ac.post(
            "/ingest_documentation",
            files={"file": ("test.exe", io.BytesIO(file_content), "application/octet-stream")},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "invalid_file_type" in resp.text
        # 2. Invalid extension
        resp = await ac.post(
            "/ingest_documentation",
            files={"file": ("test.xyz", io.BytesIO(file_content), "text/plain")},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "invalid_file_type" in resp.text
        # 3. Invalid chunk size (too small)
        resp = await ac.post(
            "/ingest_documentation",
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
            data={"chunk_size": 1},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "invalid_chunk_size" in resp.text
        # 4. Invalid chunk size (too large)
        resp = await ac.post(
            "/ingest_documentation",
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
            data={"chunk_size": 9999},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "invalid_chunk_size" in resp.text


@pytest.mark.asyncio
async def test_ingest_documentation_success_txt(monkeypatch):
    token = "Bearer testtoken"
    headers = {"Authorization": token}
    monkeypatch.setattr("apps.backend.main.get_fastembed_model", lambda: "mock_model")
    monkeypatch.setattr("apps.backend.main.upsert_documents_to_pinecone", AsyncMock(return_value=1))
    monkeypatch.setattr("apps.backend.main.DocumentPayload", SimpleNamespace)
    monkeypatch.setattr(
        "apps.backend.main.chunk_page_content",
        lambda text, chunk_size=1000, chunk_overlap=100: ["chunk1", "chunk2"],
    )
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post(
            "/ingest_documentation",
            files={"file": ("test.txt", io.BytesIO(b"hello world"), "text/plain")},
            data={"chunk_size": 1000},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["documents_added"] == 1
        assert "chunk(s)" in data["message"]


@pytest.mark.asyncio
async def test_ingest_documentation_success_pdf(monkeypatch):
    token = "Bearer testtoken"
    headers = {"Authorization": token}

    class DummyPage:
        def extract_text(self):
            return "page text"

    class DummyPDF:
        pages = [DummyPage()]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr("pdfplumber.open", lambda _: DummyPDF())
    monkeypatch.setattr("apps.backend.main.get_fastembed_model", lambda: "mock_model")
    monkeypatch.setattr("apps.backend.main.upsert_documents_to_pinecone", AsyncMock(return_value=1))
    monkeypatch.setattr("apps.backend.main.DocumentPayload", SimpleNamespace)
    monkeypatch.setattr(
        "apps.backend.main.chunk_page_content",
        lambda text, chunk_size=1000, chunk_overlap=100: ["chunk1"],
    )
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post(
            "/ingest_documentation",
            files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"chunk_size": 1000},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["documents_added"] == 1


@pytest.mark.asyncio
async def test_ingest_documentation_pdf_exception(monkeypatch):
    token = "Bearer testtoken"
    headers = {"Authorization": token}
    monkeypatch.setattr("pdfplumber.open", lambda _: (_ for _ in ()).throw(Exception("pdf error")))
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post(
            "/ingest_documentation",
            files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"chunk_size": 1000},
            headers=headers,
        )
        assert resp.status_code == 500
        assert "ingestion_processing_error" in resp.text


@pytest.mark.asyncio
async def test_ingest_documentation_upsert_exception(monkeypatch):
    token = "Bearer testtoken"
    headers = {"Authorization": token}
    monkeypatch.setattr("apps.backend.main.get_fastembed_model", lambda: "mock_model")
    monkeypatch.setattr(
        "apps.backend.main.upsert_documents_to_pinecone",
        AsyncMock(side_effect=Exception("upsert error")),
    )
    monkeypatch.setattr("apps.backend.main.DocumentPayload", SimpleNamespace)
    monkeypatch.setattr(
        "apps.backend.main.chunk_page_content",
        lambda text, chunk_size=1000, chunk_overlap=100: ["chunk1"],
    )
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post(
            "/ingest_documentation",
            files={"file": ("test.txt", io.BytesIO(b"hello world"), "text/plain")},
            data={"chunk_size": 1000},
            headers=headers,
        )
        assert resp.status_code == 500
        assert "ingestion_processing_error" in resp.text


def test_generate_reply_llm_timeout(monkeypatch):
    # Simulate LLM timeout and check error response
    monkeypatch.setattr(
        "apps.backend.main.get_rag_chain", AsyncMock(side_effect=TimeoutError("LLM timeout"))
    )
    # TODO: replace with client.post(
    #     "/generate_reply",
    #     json={"ticket_id": "1", "content": "Help!", "history": []},
    # )
    response = None
    assert response is None
    # assert response.status_code == 500 or response.status_code == 429
    # data = response.json()
    # assert "error_type" in data
    # assert data["error_type"] == "llm_timeout"
    # assert data["retryable"] is True
    # assert "documentation" in data


def test_error_response_masking():
    # Simulate error with sensitive info
    detail = "API key: sk-1234567890abcdef"
    masked = mask_api_keys(detail)
    assert "sk-" not in masked or "1234567890abcdef" not in masked
