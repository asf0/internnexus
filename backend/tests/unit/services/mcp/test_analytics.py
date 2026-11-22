from __future__ import annotations

import inspect
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin import router
from app.api.admin.mcp_usage import get_mcp_invocation_events, get_mcp_usage_stats
from app.models import Admin, MCPInvocation
from app.services.mcp import analytics as mcp_analytics_service
from tests.paths import ALEMBIC_VERSIONS
from app.services.mcp.analytics import record_mcp_invocation, sanitize_mcp_metadata


def test_sanitize_mcp_metadata_is_allowlisted_normalized_and_truncated() -> None:
    result = sanitize_mcp_metadata(
        {
            "keyword": "  software   engineering  ",
            "location": "Denver",
            "page": -4,
            "authorization": "Bearer secret",
            "apply_url": "https://employer.example/apply",
            "description": "private response content",
            "api_key": "inx_mcp_secret",
        }
    )

    assert result == {"keyword": "software engineering", "location": "Denver", "page": 0}
    serialized = str(result)
    assert "secret" not in serialized
    assert "employer.example" not in serialized
    assert "private response" not in serialized


@pytest.mark.asyncio
async def test_record_mcp_invocation_commits_sanitized_event(monkeypatch: pytest.MonkeyPatch) -> None:
    class Session:
        added: MCPInvocation | None = None
        committed = False

        def add(self, value: MCPInvocation) -> None:
            self.added = value

        async def commit(self) -> None:
            self.committed = True

    session = Session()

    class Context:
        async def __aenter__(self) -> Session:
            return session

        async def __aexit__(self, *_args) -> None:
            return None

    monkeypatch.setattr(mcp_analytics_service.db_runtime, "AsyncSessionLocal", lambda: Context())
    user_id, key_id = uuid4(), uuid4()
    await record_mcp_invocation(
        user_id=user_id,
        key_id=key_id,
        tool_name="search_jobs",
        success=True,
        duration_ms=12,
        result_count=7,
        metadata={"keyword": "python", "apply_url": "https://example.test"},
    )

    assert session.committed is True
    assert session.added is not None
    assert session.added.user_id == user_id
    assert session.added.mcp_api_key_id == key_id
    assert session.added.metadata_ == {"keyword": "python"}


@pytest.mark.asyncio
async def test_record_mcp_invocation_swallowing_write_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class Context:
        async def __aenter__(self):
            raise RuntimeError("analytics unavailable")

        async def __aexit__(self, *_args) -> None:
            return None

    monkeypatch.setattr(mcp_analytics_service.db_runtime, "AsyncSessionLocal", lambda: Context())
    await record_mcp_invocation(
        user_id=uuid4(), key_id=uuid4(), tool_name="get_job", success=True, duration_ms=1
    )


def test_admin_router_exposes_mcp_usage_endpoints() -> None:
    app = FastAPI()
    app.include_router(router)
    paths = app.openapi()["paths"]

    assert "/admin/mcp-usage/stats" in paths
    assert "/admin/mcp-usage/tools" in paths
    assert "/admin/mcp-usage/daily" in paths
    assert "/admin/mcp-usage/events" in paths


@pytest.mark.asyncio
async def test_mcp_stats_maps_aggregate_values() -> None:
    row = SimpleNamespace(
        total_calls=10,
        calls_today=2,
        calls_week=6,
        calls_month=9,
        successful=8,
        avg_duration=15.555,
        unique_users=3,
        unique_keys=4,
        search_count=5,
        avg_search_results=7.25,
    )

    class Result:
        def one(self):
            return row

    class DB:
        async def execute(self, _statement):
            return Result()

    endpoint = inspect.unwrap(get_mcp_usage_stats)
    response = await endpoint(
        request=cast(Request, object()),
        _admin=cast(Admin, SimpleNamespace()),
        db=cast(AsyncSession, DB()),
    )

    assert response.success_rate == 80.0
    assert response.average_duration_ms == 15.55
    assert response.calls_this_week == 6
    assert response.average_search_result_count == 7.25


@pytest.mark.asyncio
async def test_mcp_events_filters_and_maps_retention_safe_ids() -> None:
    event_id, key_id = uuid4(), uuid4()
    event = SimpleNamespace(
        id=event_id,
        user_id=None,
        mcp_api_key_id=key_id,
        tool_name="search_jobs",
        invoked_at=datetime.now(timezone.utc),
        success=False,
        duration_ms=20,
        job_id=None,
        result_count=None,
        error_category="validation",
        metadata_={"keyword": "python"},
    )

    class Result:
        def __init__(self, *, count=None, rows=None):
            self.count = count
            self.rows = rows

        def scalar_one(self):
            return self.count

        def scalars(self):
            return self

        def all(self):
            return self.rows

    class DB:
        statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            return Result(count=1) if len(self.statements) == 1 else Result(rows=[event])

    db = DB()
    endpoint = inspect.unwrap(get_mcp_invocation_events)
    response = await endpoint(
        request=cast(Request, object()),
        _admin=cast(Admin, SimpleNamespace()),
        db=cast(AsyncSession, db),
        page=1,
        page_size=25,
        tool="search_jobs",
        status="failure",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
    )

    assert response.total == 1
    assert response.total_pages == 1
    assert response.items[0].mcp_key_id == key_id
    assert response.items[0].called_at == event.invoked_at
    compiled = str(db.statements[0])
    assert "mcp_invocations.tool_name" in compiled
    assert "mcp_invocations.success" in compiled
    assert "mcp_invocations.invoked_at" in compiled


@pytest.mark.asyncio
async def test_mcp_events_empty_result_uses_single_empty_page() -> None:
    class Result:
        def __init__(self, *, count=None, rows=None):
            self.count = count
            self.rows = rows

        def scalar_one(self):
            return self.count

        def scalars(self):
            return self

        def all(self):
            return self.rows

    class DB:
        statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            return Result(count=0) if len(self.statements) == 1 else Result(rows=[])

    db = DB()
    endpoint = inspect.unwrap(get_mcp_invocation_events)
    response = await endpoint(
        request=cast(Request, object()),
        _admin=cast(Admin, SimpleNamespace()),
        db=cast(AsyncSession, db),
        page=1,
        page_size=25,
    )

    assert response.total == 0
    assert response.items == []
    assert response.total_pages == 1


def test_mcp_analytics_migration_uses_retention_safe_foreign_keys() -> None:
    migration = (
        ALEMBIC_VERSIONS / "0013_mcp_invocation_analytics.py"
    ).read_text()

    assert migration.count('ondelete="SET NULL"') == 3
    assert 'sa.Column("metadata", postgresql.JSONB' in migration
    assert "key_hash" not in migration
    assert "authorization" not in migration.lower()
