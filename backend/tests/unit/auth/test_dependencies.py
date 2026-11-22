from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.dependencies import _validate_password_change, get_authenticated_session, get_optional_user


def _credentials(token: str = "token") -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_claimless_token_is_rejected_after_password_change() -> None:
    user = SimpleNamespace(password_changed_at=datetime.now(timezone.utc))
    assert _validate_password_change({}, user) is False


@pytest.mark.asyncio
async def test_optional_auth_treats_invalid_token_as_anonymous() -> None:
    with patch("app.auth.dependencies.decode_access_token", return_value=None):
        result = await get_optional_user(_credentials(), AsyncMock())
    assert result is None


@pytest.mark.asyncio
async def test_missing_authoritative_session_is_rejected() -> None:
    db = AsyncMock()
    result = Mock()
    result.one_or_none.return_value = None
    db.execute.return_value = result
    payload = {"sub": str(uuid4()), "jti": str(uuid4()), "iat": 1, "exp": 2}
    with patch("app.auth.dependencies.decode_access_token", return_value=payload):
        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_session(_credentials(), db)
    assert exc_info.value.status_code == 401
    assert "revoked" in exc_info.value.detail


@pytest.mark.asyncio
async def test_active_session_resolves_user_and_session_together() -> None:
    user_id = uuid4()
    user = SimpleNamespace(id=user_id, is_deleted=False, password_changed_at=None)
    session = SimpleNamespace(jti="session-jti")
    db = AsyncMock()
    result = Mock()
    result.one_or_none.return_value = (user, session)
    db.execute.return_value = result
    payload = {"sub": str(user_id), "jti": session.jti, "iat": 1, "exp": 2}
    with patch("app.auth.dependencies.decode_access_token", return_value=payload):
        authenticated = await get_authenticated_session(_credentials(), db)
    assert authenticated.user is user
    assert authenticated.session is session
