from __future__ import annotations

import argparse
import asyncio
import functools
import inspect
import logging
import os
import re
import time
from collections import defaultdict, deque
from contextvars import ContextVar
from dataclasses import dataclass
from math import ceil
from typing import Literal
from urllib.parse import urlparse
from uuid import UUID

from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import AnyHttpUrl
from sqlalchemy.exc import SQLAlchemyError
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.infra import db as db_runtime
from app.schemas.mappers import job_to_response
from app.models import Job, User
from app.schemas.jobs import JobListResponse, JobSummaryResponse
from app.repositories.job import JobRepository
from app.services.jobs.search import JobSearchParams, JobSearchService
from app.services.mcp.api_key import MCPApiKeyService
from app.services.mcp.analytics import record_mcp_invocation
from app.services.users.user_job import JobNotFoundError, UserJobService

_JOB_NOT_FOUND = "Job not found"

PUBLIC_URL = os.getenv("MCP_PUBLIC_URL", "http://localhost:8001")
_public_url = urlparse(PUBLIC_URL)
if not _public_url.hostname:
    raise RuntimeError("MCP_PUBLIC_URL must include a hostname")
_public_hostname = _public_url.hostname
if _public_url.scheme != "https" and _public_url.hostname not in {"localhost", "127.0.0.1", "::1"}:
    raise RuntimeError("MCP_PUBLIC_URL must use HTTPS outside localhost")
_stdio_secret = os.getenv("INTERNNEXUS_MCP_API_KEY")
_rate_windows: dict[UUID, deque[float]] = defaultdict(deque)
_rate_lock = asyncio.Lock()
logger = logging.getLogger(__name__)


class InternNexusTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        async with db_runtime.AsyncSessionLocal() as session:
            authenticated = await MCPApiKeyService(session).authenticate_principal(token)
            if authenticated is None:
                return None
            return AccessToken(
                token=token,
                client_id="internnexus-mcp-key",
                scopes=["jobs"],
                subject=str(authenticated.user.id),
                claims={
                    "user_id": str(authenticated.user.id),
                    "mcp_key_id": str(authenticated.key_id),
                },
            )


MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8001"))
MCP_STREAMABLE_HTTP_PATH = "/mcp"
MCP_STATELESS_HTTP = True
MCP_JSON_RESPONSE = True
TRANSPORT_SECURITY = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        _public_hostname,
        f"{_public_hostname}:*",
        "localhost",
        "localhost:*",
        "127.0.0.1",
        "127.0.0.1:*",
        "mcp",
        "mcp:*",
    ],
    allowed_origins=[f"{_public_url.scheme}://{_public_url.netloc}"],
)

mcp = MCPServer(
    "InternNexus",
    instructions=(
        "Search InternNexus jobs and manage the authenticated user's saved/applied state. "
        "Put location, company, category, job type, and work mode in their dedicated filters; "
        "pipe-separate multiple filter values. Ordinary keywords default to match_mode='all'. "
        "Inspect total and next_page and fetch additional pages when needed. Searches default to jobs "
        "posted in the last 120 days; retry with posted_within='all' for older active jobs. For sparse "
        "results retry with match_mode='any', fewer filters, or posted_within='all'. Use get_job only "
        "after selecting candidates that need full descriptions. Employer application URLs are only "
        "available through get_application_link or apply_to_job. get_application_link records a link "
        "request without marking applied; apply_to_job marks applied and returns the tracked link. "
        "Neither tool submits an external application form. Do not retry an unchanged failed tool call "
        "more than once; report the failure to the user instead."
    ),
    token_verifier=InternNexusTokenVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(PUBLIC_URL),
        resource_server_url=AnyHttpUrl(PUBLIC_URL),
        required_scopes=["jobs"],
        # Tokens are opaque API keys validated by our verifier, not JWTs with an
        # RFC 8707 audience, so the SDK must not compare AccessToken.resource.
        validate_token_resource=False,
    ),
)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@dataclass(frozen=True)
class MCPAuthContext:
    user: User
    key_id: UUID


_invocation_context: ContextVar[MCPAuthContext | None] = ContextVar("mcp_invocation_context", default=None)


async def _current_context() -> MCPAuthContext:
    existing = _invocation_context.get()
    if existing is not None:
        return existing
    access_token = get_access_token()
    if access_token and access_token.subject:
        user_id = UUID(access_token.subject)
        key_id_raw = (access_token.claims or {}).get("mcp_key_id")
        if not key_id_raw:
            raise PermissionError("MCP key context missing")
        async with db_runtime.AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if user is not None and not user.is_deleted:
                await _enforce_rate_limit(user.id)
                return MCPAuthContext(user=user, key_id=UUID(str(key_id_raw)))
    if _stdio_secret:
        async with db_runtime.AsyncSessionLocal() as session:
            authenticated = await MCPApiKeyService(session).authenticate_principal(_stdio_secret)
            if authenticated is not None:
                await _enforce_rate_limit(authenticated.user.id)
                return MCPAuthContext(user=authenticated.user, key_id=authenticated.key_id)
    raise PermissionError("Authentication required")


async def _current_user() -> User:
    return (await _current_context()).user


async def _enforce_rate_limit(user_id: UUID, limit: int = 120) -> None:
    now = time.monotonic()
    async with _rate_lock:
        window = _rate_windows[user_id]
        while window and window[0] <= now - 60:
            window.popleft()
        if len(window) >= limit:
            raise RuntimeError("MCP rate limit exceeded; retry in one minute")
        window.append(now)


def _job_detail_dict(job: Job) -> dict:
    payload = job_to_response(job).model_dump(mode="json")
    payload.pop("apply_url", None)
    return payload


def _compact_job_dict(job: Job | JobSummaryResponse) -> dict:
    job_type = job.job_type
    work_mode = job.work_mode
    posted_at = job.posted_at
    return {
        "id": str(job.id),
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "job_category": job.job_category,
        "job_type": getattr(job_type, "value", job_type),
        "work_mode": getattr(work_mode, "value", work_mode),
        "posted_at": posted_at.isoformat() if posted_at else None,
    }


def _search_result_dict(result: JobListResponse) -> dict:
    total_pages = ceil(result.total / result.page_size) if result.total else 0
    has_more = result.page < total_pages
    return {
        "items": [_compact_job_dict(job) for job in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": total_pages,
        "has_more": has_more,
        "next_page": result.page + 1 if has_more else None,
        "default_recency_days": 120,
    }


READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
MUTATION = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
LINK_REQUEST = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=True
)


def _error_category(exc: Exception) -> str:
    if isinstance(exc, PermissionError):
        return "authentication_error"
    if isinstance(exc, ValueError):
        return "validation_error"
    if isinstance(exc, RuntimeError) and "rate limit" in str(exc).lower():
        return "rate_limit_error"
    if isinstance(exc, SQLAlchemyError):
        return "database_error"
    return "internal_error"


def _normalized_metadata(arguments: dict) -> dict:
    allowed = {
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
    metadata: dict = {}
    for key in allowed:
        value = arguments.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            value = re.sub(r"\s+", " ", value).strip()[:100]
        metadata[key] = value
    return metadata


def _result_count(result: object) -> int | None:
    if isinstance(result, dict) and isinstance(result.get("items"), list):
        return len(result["items"])
    return None


def _log_tool_failure(
    tool_name: str, error_category: str, context: MCPAuthContext | None, job_id: object
) -> None:
    if error_category not in {"database_error", "internal_error"}:
        return
    logger.exception(
        "MCP tool invocation failed",
        extra={
            "mcp_tool": tool_name,
            "error_category": error_category,
            "user_id": str(context.user.id) if context else None,
            "mcp_key_id": str(context.key_id) if context else None,
            "job_id": str(job_id) if job_id else None,
        },
    )


def tracked_tool(tool_name: str):
    """Record one durable analytics event for every tool function invocation."""

    def decorator(func):
        signature = inspect.signature(func)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            started = time.perf_counter()
            context: MCPAuthContext | None = None
            token = None
            success = False
            result_count: int | None = None
            error_category: str | None = None
            bound = signature.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            job_id = bound.arguments.get("job_id")
            try:
                context = await _current_context()
                token = _invocation_context.set(context)
                result = await func(*args, **kwargs)
                success = True
                result_count = _result_count(result)
                return result
            except Exception as exc:
                error_category = _error_category(exc)
                _log_tool_failure(tool_name, error_category, context, job_id)
                raise
            finally:
                duration_ms = max(0, round((time.perf_counter() - started) * 1000))
                if token is not None:
                    _invocation_context.reset(token)
                await record_mcp_invocation(
                    user_id=context.user.id if context else None,
                    key_id=context.key_id if context else None,
                    tool_name=tool_name,
                    success=success,
                    duration_ms=duration_ms,
                    job_id=job_id,
                    result_count=result_count,
                    metadata=_normalized_metadata(dict(bound.arguments)),
                    error_category=error_category,
                )

        return wrapper

    return decorator


@mcp.tool(annotations=READ_ONLY)
@tracked_tool("search_jobs")
async def search_jobs(
    keyword: str | None = None,
    company: str | None = None,
    location: str | None = None,
    category: str | None = None,
    job_type: str | None = None,
    work_mode: str | None = None,
    posted_within: Literal["24h", "7d", "30d", "all"] | None = None,
    match_mode: Literal["all", "any"] = "all",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Search active jobs with compact results. Defaults to 120 days and 50 items; maximum page size is 50.

    Use dedicated filters rather than keywords for company, location, category, job type, and work mode.
    Pipe-separate multiple filter values. Ordinary keywords use all/any matching; explicit Boolean operators
    take precedence. Follow next_page, and broaden sparse searches with any, fewer filters, or posted_within=all.
    """
    await _current_user()
    async with db_runtime.AsyncSessionLocal() as session:
        result = await JobSearchService(session).search(
            JobSearchParams(
                page=page,
                page_size=min(page_size, 50),
                search=keyword,
                company=company,
                location=location,
                category=category,
                job_type=job_type,
                work_mode=work_mode,
                posted_within=posted_within,
                active_only=True,
                match_mode=match_mode,
            )
        )
        return _search_result_dict(result)


@mcp.tool(annotations=READ_ONLY)
@tracked_tool("get_job")
async def get_job(job_id: UUID) -> dict:
    """Get one active job by UUID."""
    await _current_user()
    async with db_runtime.AsyncSessionLocal() as session:
        job = await JobRepository(session).get_by_id(job_id)
        if job is None or job.is_active is not True:
            raise ValueError(_JOB_NOT_FOUND)
        return _job_detail_dict(job)


@mcp.tool(annotations=READ_ONLY)
@tracked_tool("list_saved_jobs")
async def list_saved_jobs(limit: int = 50) -> dict:
    """List the authenticated user's saved jobs, newest first (maximum 50)."""
    user = await _current_user()
    async with db_runtime.AsyncSessionLocal() as session:
        rows = await UserJobService(session).list_saved(user.id, limit)
        return {
            "items": [
                {"saved_at": saved.created_at.isoformat(), "job": _compact_job_dict(job)}
                for saved, job in rows
            ]
        }


@mcp.tool(annotations=MUTATION)
@tracked_tool("save_job")
async def save_job(job_id: UUID) -> dict:
    """Idempotently save an active job for the authenticated user."""
    user = await _current_user()
    async with db_runtime.AsyncSessionLocal() as session:
        try:
            created = await UserJobService(session).save(user.id, job_id)
        except JobNotFoundError as exc:
            raise ValueError(_JOB_NOT_FOUND) from exc
        return {"job_id": str(job_id), "saved": True, "created": created}


@mcp.tool(annotations=MUTATION)
@tracked_tool("unsave_job")
async def unsave_job(job_id: UUID) -> dict:
    """Idempotently remove a job from the authenticated user's saved jobs."""
    user = await _current_user()
    async with db_runtime.AsyncSessionLocal() as session:
        removed = await UserJobService(session).unsave(user.id, job_id)
        return {"job_id": str(job_id), "saved": False, "removed": removed}


@mcp.tool(annotations=READ_ONLY)
@tracked_tool("list_applied_jobs")
async def list_applied_jobs(limit: int = 50) -> dict:
    """List jobs the authenticated user marked as applied, newest first (maximum 50)."""
    user = await _current_user()
    async with db_runtime.AsyncSessionLocal() as session:
        rows = await UserJobService(session).list_applied(user.id, limit)
        return {
            "items": [
                {"applied_at": applied.applied_at.isoformat(), "job": _compact_job_dict(job)}
                for applied, job in rows
            ]
        }


@mcp.tool(annotations=LINK_REQUEST)
@tracked_tool("get_application_link")
async def get_application_link(job_id: UUID) -> dict:
    """Record an application-link request and return the tracked employer URL without marking the job applied."""
    user = await _current_user()
    async with db_runtime.AsyncSessionLocal() as session:
        service = UserJobService(session)
        try:
            apply_url = await service.get_application_link(user.id, job_id)
        except JobNotFoundError as exc:
            raise ValueError(_JOB_NOT_FOUND) from exc
        return {
            "job_id": str(job_id),
            "apply_url": apply_url,
            "marked_applied": False,
            "notice": "Complete the application on the employer's site.",
        }


@mcp.tool(annotations=LINK_REQUEST)
@tracked_tool("apply_to_job")
async def apply_to_job(job_id: UUID) -> dict:
    """Mark a job as applied and return its employer URL. This does not submit an external application form."""
    user = await _current_user()
    async with db_runtime.AsyncSessionLocal() as session:
        service = UserJobService(session)
        try:
            apply_url, created = await service.apply_from_mcp(user.id, job_id)
        except JobNotFoundError as exc:
            raise ValueError(_JOB_NOT_FOUND) from exc
        return {
            "job_id": str(job_id),
            "marked_applied": True,
            "created": created,
            "apply_url": apply_url,
            "notice": "InternNexus recorded your state; complete the application on the employer's site.",
        }


@mcp.tool(annotations=MUTATION)
@tracked_tool("unmark_applied")
async def unmark_applied(job_id: UUID) -> dict:
    """Remove only InternNexus's applied marker; this cannot undo an external application."""
    user = await _current_user()
    async with db_runtime.AsyncSessionLocal() as session:
        removed = await UserJobService(session).unmark_applied(user.id, job_id)
        return {"job_id": str(job_id), "marked_applied": False, "removed": removed}


def main() -> None:
    parser = argparse.ArgumentParser(description="InternNexus MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default=os.getenv("MCP_TRANSPORT", "stdio"),
    )
    args = parser.parse_args()
    if args.transport == "stdio" and not _stdio_secret:
        parser.error("INTERNNEXUS_MCP_API_KEY is required for stdio transport")
    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return
    mcp.run(
        transport="streamable-http",
        host=MCP_HOST,
        port=MCP_PORT,
        streamable_http_path=MCP_STREAMABLE_HTTP_PATH,
        stateless_http=MCP_STATELESS_HTTP,
        json_response=MCP_JSON_RESPONSE,
        transport_security=TRANSPORT_SECURITY,
    )


if __name__ == "__main__":
    main()
