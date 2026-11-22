import logging
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import MissingGreenlet

from app import mcp_server
from app.mcp_server import _error_category, _job_detail_dict, _search_result_dict, mcp, tracked_tool


@pytest.mark.asyncio
async def test_mcp_exposes_only_v1_job_tools():
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    assert set(tools) == {
        "search_jobs",
        "get_job",
        "list_saved_jobs",
        "save_job",
        "unsave_job",
        "list_applied_jobs",
        "get_application_link",
        "apply_to_job",
        "unmark_applied",
    }
    assert tools["search_jobs"].annotations.read_only_hint is True
    assert tools["get_job"].annotations.read_only_hint is True
    assert tools["save_job"].annotations.read_only_hint is False
    assert tools["apply_to_job"].annotations.idempotent_hint is False
    assert tools["get_application_link"].annotations.idempotent_hint is False
    search_schema = tools["search_jobs"].input_schema["properties"]
    assert search_schema["page_size"]["default"] == 50
    assert search_schema["match_mode"]["default"] == "all"


def test_mcp_is_stateless_streamable_http():
    assert mcp_server.MCP_STATELESS_HTTP is True
    assert mcp_server.MCP_JSON_RESPONSE is True
    assert mcp_server.MCP_STREAMABLE_HTTP_PATH == "/mcp"
    assert "localhost" in mcp_server.TRANSPORT_SECURITY.allowed_hosts
    assert "localhost:*" in mcp_server.TRANSPORT_SECURITY.allowed_hosts
    assert "Do not retry an unchanged failed tool call more than once" in mcp.instructions


def test_sqlalchemy_errors_are_reported_as_database_errors():
    assert _error_category(MissingGreenlet("async attribute load attempted")) == "database_error"


@pytest.mark.asyncio
async def test_database_tool_failure_is_logged_and_recorded(monkeypatch, caplog):
    user_id, key_id, job_id = uuid4(), uuid4(), uuid4()
    context = SimpleNamespace(user=SimpleNamespace(id=user_id), key_id=key_id)
    record_invocation = AsyncMock()
    monkeypatch.setattr(mcp_server, "_current_context", AsyncMock(return_value=context))
    monkeypatch.setattr(mcp_server, "record_mcp_invocation", record_invocation)

    @tracked_tool("failing_tool")
    async def failing_tool(job_id):
        raise MissingGreenlet("async attribute load attempted")

    with caplog.at_level(logging.ERROR, logger="app.mcp_server"):
        with pytest.raises(MissingGreenlet):
            await failing_tool(job_id)

    assert "MCP tool invocation failed" in caplog.text
    event = record_invocation.await_args.kwargs
    assert event["success"] is False
    assert event["error_category"] == "database_error"
    assert event["user_id"] == user_id
    assert event["key_id"] == key_id
    assert event["job_id"] == job_id


def test_compact_search_payload_has_continuation_metadata_and_no_sensitive_fields():
    job = SimpleNamespace(
        id=uuid4(),
        title="Software Intern",
        company="Acme",
        location="Denver, CO",
        job_category="software",
        job_type="internship",
        work_mode="hybrid",
        posted_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        apply_url="https://employer.example/apply",
        description_text="Full description",
    )

    payload = _search_result_dict(
        SimpleNamespace(items=[job], total=101, page=2, page_size=50)
    )

    assert payload["total_pages"] == 3
    assert payload["has_more"] is True
    assert payload["next_page"] == 3
    assert payload["default_recency_days"] == 120
    assert "apply_url" not in payload["items"][0]
    assert "description_text" not in payload["items"][0]


def test_get_job_detail_keeps_description_but_removes_employer_url():
    job = SimpleNamespace(
        id=uuid4(),
        source="greenhouse",
        title="Software Intern",
        company="Acme",
        location="Denver, CO",
        city="Denver",
        state="CO",
        country="USA",
        apply_url="https://employer.example/apply",
        description_text="Full description",
        job_category="software",
        job_type="internship",
        work_mode="hybrid",
        posted_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        is_active=True,
    )

    payload = _job_detail_dict(job)

    assert payload["description_html"] == "Full description"
    assert payload["description_truncated"] is False
    assert "apply_url" not in payload
