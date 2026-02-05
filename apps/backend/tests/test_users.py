import hashlib
from unittest.mock import AsyncMock

import pytest

from apps.backend.app.auth import users as users_module
from apps.backend.app.auth.models import User


@pytest.mark.asyncio
async def test_get_user_by_username_found():
    dummy_user = User(username="alice", hashed_password="hash")
    session = AsyncMock()

    # Create a mock result that mimics SQLAlchemy's Result object
    class MockResult:
        def scalars(self):
            return self

        def first(self):
            return dummy_user

    session.execute.return_value = MockResult()
    user = await users_module.get_user_by_username(session, "alice")
    assert user is dummy_user
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_by_username_not_found():
    session = AsyncMock()

    class MockResult:
        def scalars(self):
            return self

        def first(self):
            return None

    session.execute.return_value = MockResult()
    user = await users_module.get_user_by_username(session, "bob")
    assert user is None
    session.execute.assert_called_once()


def test_verify_password_success():
    password = "secret"
    hashed = hashlib.sha256(password.encode()).hexdigest()
    assert users_module.verify_password(password, hashed)


def test_verify_password_failure():
    password = "secret"
    hashed = hashlib.sha256("other".encode()).hexdigest()
    assert not users_module.verify_password(password, hashed)


@pytest.mark.asyncio
async def test_create_user_creates_and_returns_user():
    session = AsyncMock()
    session.add = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    user = await users_module.create_user(session, "eve", "pw123")
    assert user.username == "eve"
    assert users_module.verify_password("pw123", user.hashed_password)
    session.add.assert_called_once()
    session.commit.assert_called_once()
    session.refresh.assert_called_once_with(user)


@pytest.mark.asyncio
async def test_create_user_duplicate(monkeypatch):
    session = AsyncMock()
    session.add = AsyncMock(side_effect=Exception("IntegrityError"))
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    with pytest.raises(Exception):
        await users_module.create_user(session, "eve", "pw123")
