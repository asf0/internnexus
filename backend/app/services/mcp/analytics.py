"""Best-effort, privacy-safe MCP invocation analytics."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from app.infra import db as db_runtime
from app.models import MCPInvocation

logger = logging.getLogger(__name__)

_METADATA_KEYS = {
    "keyword",
    "company",
    "location",
    "category",
    "job_type",
    "work_mode",
    "posted_within",
    "match_mode",
    "page",
    "page_size",
    "limit",
}
_SAFE_CATEGORY = re.compile(r"^[a-z][a-z0-9_]{0,79}$")


def sanitize_mcp_metadata(metadata: Mapping[str, Any] | None) -> dict[str, str | int | bool | list[str]]:
    """Keep only normalized search/filter values; never retain arbitrary payload data."""
    clean: dict[str, str | int | bool | list[str]] = {}
    for key, value in (metadata or {}).items():
        if key not in _METADATA_KEYS or value is None:
            continue
        if isinstance(value, bool):
            clean[key] = value
        elif isinstance(value, int):
            clean[key] = max(0, min(value, 10_000))
        elif isinstance(value, str):
            normalized = " ".join(value.split()).strip()[:200]
            if normalized:
                clean[key] = normalized
        elif isinstance(value, (list, tuple)):
            values = [" ".join(str(item).split()).strip()[:100] for item in value[:10]]
            clean[key] = [item for item in values if item]
    return clean


def categorize_mcp_error(error: BaseException) -> str:
    """Map an exception to a stable category without storing its message."""
    name = type(error).__name__.lower()
    if isinstance(error, PermissionError):
        return "authentication"
    if isinstance(error, (ValueError, TypeError)):
        return "validation"
    if "notfound" in name or "not_found" in name:
        return "not_found"
    if "rate" in name and "limit" in name:
        return "rate_limit"
    if "sql" in name or "database" in name or "integrity" in name:
        return "database"
    return "internal"


async def record_mcp_invocation(
    *,
    user_id: UUID | None,
    key_id: UUID | None,
    tool_name: str,
    success: bool,
    duration_ms: int,
    job_id: UUID | None = None,
    result_count: int | None = None,
    metadata: Mapping[str, Any] | None = None,
    error_category: str | None = None,
) -> None:
    """Write one event in an independent session without affecting the tool result."""
    category = error_category if error_category and _SAFE_CATEGORY.fullmatch(error_category) else None
    try:
        async with db_runtime.AsyncSessionLocal() as session:
            session.add(
                MCPInvocation(
                    user_id=user_id,
                    mcp_api_key_id=key_id,
                    tool_name=tool_name[:80],
                    success=success,
                    duration_ms=max(0, min(int(duration_ms), 2_147_483_647)),
                    job_id=job_id,
                    result_count=None if result_count is None else max(0, int(result_count)),
                    error_category=category,
                    metadata_=sanitize_mcp_metadata(metadata),
                )
            )
            await session.commit()
    except Exception:
        logger.exception("Failed to record MCP invocation analytics", extra={"tool_name": tool_name[:80]})
