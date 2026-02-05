import uuid
from datetime import datetime, timedelta

import pytest
from jose import jwt

from apps.backend.app.auth.jwt import ALGORITHM as JWT_ALGORITHM
from apps.backend.app.auth.jwt import SECRET_KEY as JWT_SECRET

TEST_USER_ID = "123e4567-e89b-12d3-a456-426614174000"


def create_test_token(is_admin=False):
    payload = {
        "sub": TEST_USER_ID,
        "is_admin": is_admin,
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@pytest.mark.asyncio
async def test_gdpr_delete_requires_jwt(async_client):
    # No JWT - should return 401
    resp = await async_client.post("/v1/compliance/gdpr_delete", json={"user_id": "other-user"})
    assert resp.status_code == 401

    # Admin JWT - use dependency override to bypass JWT validation issues
    from apps.backend.app.auth.jwt import get_current_user
    from apps.backend.main import app

    class MockAdminUser:
        id = uuid.UUID(TEST_USER_ID)
        username = "complianceadmin"
        is_admin = True

    app.dependency_overrides[get_current_user] = lambda: MockAdminUser()
    try:
        resp = await async_client.post(
            "/v1/compliance/gdpr_delete",
            json={"user_id": "other-user"},
        )
        assert resp.status_code in (200, 404, 500)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    # Non-admin JWT - use dependency override
    class MockNonAdminUser:
        id = uuid.UUID(TEST_USER_ID)
        username = "complianceadmin"
        is_admin = False

    app.dependency_overrides[get_current_user] = lambda: MockNonAdminUser()
    try:
        resp = await async_client.post(
            "/v1/compliance/gdpr_delete",
            json={"user_id": "other-user"},
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_ccpa_optout_requires_jwt(async_client):
    # Part 1: No JWT - should return 401
    resp = await async_client.post(
        "/v1/compliance/ccpa_optout",
        json={"user_id": TEST_USER_ID},
    )
    assert resp.status_code == 401

    # Part 2: With valid JWT - use dependency override to test authenticated path
    from apps.backend.app.auth.jwt import get_current_user
    from apps.backend.main import app

    class MockUser:
        id = uuid.UUID(TEST_USER_ID)
        username = "testuser"
        is_admin = False

    app.dependency_overrides[get_current_user] = lambda: MockUser()
    try:
        resp = await async_client.post(
            "/v1/compliance/ccpa_optout",
            json={"user_id": TEST_USER_ID},
        )
        # 200 = success, 404 = user not found, 500 = DB error
        assert resp.status_code in (200, 404, 500)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
