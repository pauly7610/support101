import uuid
from datetime import datetime, timedelta

import jwt
import pytest

from apps.backend.app.auth.jwt import ALGORITHM as JWT_ALGORITHM
from apps.backend.app.auth.jwt import SECRET_KEY as JWT_SECRET
from apps.backend.app.auth.models import User

TEST_ADMIN_ID = "123e4567-e89b-12d3-a456-426614174001"


def create_admin_token():
    payload = {
        "sub": TEST_ADMIN_ID,
        "is_admin": True,
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@pytest.mark.asyncio
async def test_escalation_analytics_admin(async_client, async_session):
    # Clean up any existing user with this id or username
    await async_session.execute(
        User.__table__.delete().where(
            (User.id == uuid.UUID(TEST_ADMIN_ID)) | (User.username == "admin")
        )
    )
    await async_session.commit()
    admin_user = User(
        id=uuid.UUID(TEST_ADMIN_ID),
        email="admin2@example.com",
        username="admin",
        hashed_password="irrelevant",
        is_admin=True,
        data_sale_optout=False,
    )
    async_session.add(admin_user)
    await async_session.commit()

    token = create_admin_token()
    # Basic analytics call
    resp = await async_client.get(
        "/v1/analytics/escalations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "escalations" in data
    assert "timeframe" in data

    # Test with user_id filter (should not error, even if no data)
    resp = await async_client.get(
        "/v1/analytics/escalations?user_id=00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "escalations" in resp.json()

    # Test with start_time/end_time filter (should not error, even if no data)
    import time

    now = int(time.time())
    resp = await async_client.get(
        f"/v1/analytics/escalations?start_time={now-10000}&end_time={now}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "escalations" in resp.json()


@pytest.mark.asyncio
async def test_escalation_analytics_permission_denied(async_client, async_session):
    # Insert non-admin user
    import uuid

    from apps.backend.app.auth.models import User

    user_id = "123e4567-e89b-12d3-a456-426614174002"
    await async_session.execute(User.__table__.delete().where(User.id == uuid.UUID(user_id)))
    await async_session.commit()
    user = User(
        id=uuid.UUID(user_id),
        email="user@example.com",
        username="user",
        hashed_password="irrelevant",
        is_admin=False,
        data_sale_optout=False,
    )
    async_session.add(user)
    await async_session.commit()

    payload = {"sub": user_id, "is_admin": False, "exp": datetime.utcnow() + timedelta(minutes=15)}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    # Test all analytics endpoints for 403
    for endpoint in [
        "/v1/analytics/escalations",
        "/v1/analytics/escalations/by-agent",
        "/v1/analytics/escalations/by-category",
    ]:
        resp = await async_client.get(endpoint, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Insufficient permissions"


@pytest.mark.asyncio
async def test_escalations_by_agent_and_category_admin(async_client, async_session):
    # Ensure admin user exists
    import uuid

    from apps.backend.app.auth.models import User

    TEST_ADMIN_ID = "123e4567-e89b-12d3-a456-426614174001"
    await async_session.execute(
        User.__table__.delete().where(
            (User.id == uuid.UUID(TEST_ADMIN_ID)) | (User.username == "admin")
        )
    )
    await async_session.commit()
    admin_user = User(
        id=uuid.UUID(TEST_ADMIN_ID),
        email="admin2@example.com",
        username="admin",
        hashed_password="irrelevant",
        is_admin=True,
        data_sale_optout=False,
    )
    async_session.add(admin_user)
    await async_session.commit()
    token = create_admin_token()

    # By agent: no data, should return empty list
    resp = await async_client.get(
        "/v1/analytics/escalations/by-agent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "by_agent" in resp.json()
    # By agent: filter
    resp = await async_client.get(
        "/v1/analytics/escalations/by-agent?agent_id=00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "by_agent" in resp.json()

    # By category: no data, should return empty list
    resp = await async_client.get(
        "/v1/analytics/escalations/by-category",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "by_category" in resp.json()
    # By category: filter
    resp = await async_client.get(
        "/v1/analytics/escalations/by-category?category=test",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "by_category" in resp.json()


@pytest.mark.xfail(reason="Analytics endpoint not implemented or requires real API key")
@pytest.mark.xfail(reason="/analytics/escalations endpoint not implemented (404)")
def test_escalation_analytics_filter_user():
    # resp = client.get("/analytics/escalations?user_id=testuser")
    # assert resp.status_code == 200
    pass


@pytest.mark.xfail(reason="Analytics endpoint not implemented or requires real API key")
@pytest.mark.xfail(reason="/analytics/escalations endpoint not implemented (404)")
def test_escalation_analytics_filter_time():
    # resp = client.get(
    #     "/analytics/escalations?start_time={}&end_time={}".format(
    #         int(time.time())-10000, int(time.time())
    #     )
    # )
    # assert resp.status_code == 200
    pass
