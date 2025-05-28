from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from jose import jwt

from apps.backend.app.auth import jwt as jwt_module

SECRET_KEY = jwt_module.SECRET_KEY
ALGORITHM = jwt_module.ALGORITHM


@pytest.fixture
def user_dict():
    return {"sub": "user123", "is_admin": True}


def test_create_access_token(user_dict):
    token = jwt_module.create_access_token(user_dict)
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    for k, v in user_dict.items():
        assert decoded[k] == v
    assert "exp" in decoded


@pytest.mark.asyncio
async def test_get_current_user_valid(monkeypatch, user_dict):
    token = jwt_module.create_access_token(user_dict)

    class DummyUser:

        def __init__(self, id):
            self.id = id
            self.is_admin = True

    class DummySession:
        async def execute(self, stmt):

            class DummyResult:
                def scalar_one_or_none(self):
                    return DummyUser("user123")

            return DummyResult()

    monkeypatch.setattr(jwt_module, "get_db", lambda: DummySession())
    user = await jwt_module.get_current_user(token, DummySession())
    assert user.id == "user123"
    assert user.is_admin is True


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    with pytest.raises(HTTPException) as exc:
        await jwt_module.get_current_user("invalid.token.here", None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_expired_token(monkeypatch):
    expired_payload = {"sub": "user123", "exp": datetime.utcnow() - timedelta(minutes=1)}
    expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        await jwt_module.get_current_user(expired_token, None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_no_user(monkeypatch, user_dict):
    token = jwt_module.create_access_token(user_dict)

    class DummySession:
        async def execute(self, stmt):
            class DummyResult:
                def scalar_one_or_none(self):
                    return None

            return DummyResult()

    monkeypatch.setattr(jwt_module, "get_db", lambda: DummySession())
    with pytest.raises(HTTPException) as exc:
        await jwt_module.get_current_user(token, DummySession())
    assert exc.value.status_code == 404
