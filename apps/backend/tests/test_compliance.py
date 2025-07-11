import uuid
from datetime import datetime, timedelta

import pytest
from jose import jwt

from apps.backend.app.auth.jwt import ALGORITHM as JWT_ALGORITHM
from apps.backend.app.auth.jwt import SECRET_KEY as JWT_SECRET
from apps.backend.app.auth.models import User

TEST_USER_ID = "123e4567-e89b-12d3-a456-426614174000"


def create_test_token(is_admin=False):
    payload = {
        "sub": TEST_USER_ID,
        "is_admin": is_admin,
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@pytest.mark.asyncio
async def test_gdpr_delete_requires_jwt(async_client, async_session):
    # Clean up any existing user with this id or username
    await async_session.execute(
        User.__table__.delete().where(
            (User.id == uuid.UUID(TEST_USER_ID)) | (User.username == "admin")
        )
    )
    await async_session.commit()

    # Insert admin user into DB
    admin_user = User(
        id=uuid.UUID(TEST_USER_ID),
        email="admin@example.com",
        username="admin",
        hashed_password="irrelevant",
        is_admin=True,
        data_sale_optout=False,
    )
    async_session.add(admin_user)
    await async_session.commit()

    # No JWT
    resp = await async_client.post(f"/v1/compliance/gdpr_delete?user_id={TEST_USER_ID}")
    assert resp.status_code == 401

    # Admin JWT
    token = create_test_token(is_admin=True)
    resp = await async_client.post(
        f"/v1/compliance/gdpr_delete?user_id={TEST_USER_ID}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 404)

    # Non-admin JWT
    token = create_test_token(is_admin=False)
    resp = await async_client.post(
        f"/v1/compliance/gdpr_delete?user_id={TEST_USER_ID}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (401, 403)

    # Expired JWT
    import jwt as pyjwt

    expired = pyjwt.encode(
        {"sub": TEST_USER_ID, "is_admin": True, "exp": datetime.utcnow() - timedelta(minutes=1)},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    resp = await async_client.post(
        f"/v1/compliance/gdpr_delete?user_id={TEST_USER_ID}",
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert resp.status_code == 401

    # Malformed JWT
    resp = await async_client.post(
        f"/v1/compliance/gdpr_delete?user_id={TEST_USER_ID}",
        headers={"Authorization": "Bearer not.a.jwt"},
    )
    assert resp.status_code == 401

    # DB error simulation
    from unittest.mock import AsyncMock, patch

    with patch("apps.backend.app.compliance.router.get_db", new_callable=AsyncMock) as db_mock:
        db_mock.return_value.execute = AsyncMock(side_effect=Exception("DB error"))
        db_mock.return_value.commit = AsyncMock()

        resp = await async_client.post(
            f"/v1/compliance/gdpr_delete?user_id={TEST_USER_ID}",
            headers={"Authorization": f"Bearer {create_test_token(is_admin=True)}"},
        )
        assert resp.status_code in (500, 503)


@pytest.mark.asyncio
async def test_ccpa_optout_requires_jwt(async_client):
    token = create_test_token()
    resp = await async_client.post(
        f"/v1/compliance/ccpa_optout?user_id={TEST_USER_ID}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 404)
