from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models import MCPApiKey, User
from app.services.mcp.api_key import MCPApiKeyService, MCP_KEY_PREFIX


def mock_session():
    session = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_create_stores_hash_and_returns_secret_once():
    session = mock_session()
    service = MCPApiKeyService(session)
    created = await service.create(uuid4(), "Codex", 90)

    assert created.secret.startswith(MCP_KEY_PREFIX)
    assert created.record.key_hash == service.hash_secret(created.secret)
    assert created.secret not in created.record.key_hash
    assert created.record.key_prefix == created.secret[:20]
    session.add.assert_called_once_with(created.record)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_caps_expiration_at_365_days():
    session = mock_session()
    before = datetime.now(timezone.utc)
    created = await MCPApiKeyService(session).create(uuid4(), "Agent", 999)
    assert before + timedelta(days=364) < created.record.expires_at <= before + timedelta(days=366)


@pytest.mark.asyncio
async def test_authenticate_updates_last_used_for_active_key():
    session = mock_session()
    secret = MCP_KEY_PREFIX + "secret"
    record = MagicMock(spec=MCPApiKey)
    record.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    record.revoked_at = None
    user = MagicMock(spec=User)
    user.is_deleted = False
    result = MagicMock()
    result.one_or_none.return_value = (record, user)
    session.execute.return_value = result

    authenticated = await MCPApiKeyService(session).authenticate(secret)
    assert authenticated is user
    assert record.last_used_at is not None
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_authenticate_principal_retains_key_id_for_analytics():
    session = mock_session()
    secret = MCP_KEY_PREFIX + "secret"
    record = MagicMock(spec=MCPApiKey)
    record.id = uuid4()
    record.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    record.revoked_at = None
    user = MagicMock(spec=User)
    user.is_deleted = False
    result = MagicMock()
    result.one_or_none.return_value = (record, user)
    session.execute.return_value = result

    principal = await MCPApiKeyService(session).authenticate_principal(secret)

    assert principal is not None
    assert principal.user is user
    assert principal.key_id == record.id


@pytest.mark.asyncio
@pytest.mark.parametrize("revoked,expired", [(True, False), (False, True)])
async def test_authenticate_rejects_revoked_or_expired_key(revoked: bool, expired: bool):
    session = mock_session()
    record = MagicMock(spec=MCPApiKey)
    record.expires_at = datetime.now(timezone.utc) + timedelta(days=-1 if expired else 1)
    record.revoked_at = datetime.now(timezone.utc) if revoked else None
    user = MagicMock(spec=User)
    user.is_deleted = False
    result = MagicMock()
    result.one_or_none.return_value = (record, user)
    session.execute.return_value = result
    assert await MCPApiKeyService(session).authenticate(MCP_KEY_PREFIX + "secret") is None
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_authenticate_rejects_wrong_prefix_without_query():
    session = mock_session()
    assert await MCPApiKeyService(session).authenticate("wrong") is None
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_for_user_excludes_revoked_keys():
    session = mock_session()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result

    await MCPApiKeyService(session).list_for_user(uuid4())

    statement = str(session.execute.await_args.args[0])
    assert "mcp_api_keys.revoked_at IS NULL" in statement
