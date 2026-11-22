"""Administrator-facing MCP invocation analytics."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.admin import (
    AdminListResponse,
    MCPDailyUsageResponse,
    MCPInvocationResponse,
    MCPToolUsageResponse,
    MCPUsageStatsResponse,
)
from app.auth.dependencies import AdminDep
from app.infra.db import get_db
from app.models import MCPInvocation
from app.infra.rate_limiter import RATE_LIMITS, limiter

from .shared import paginate

router = APIRouter(prefix="/mcp-usage")


def _percentage(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100, 2) if denominator else 0.0


@router.get("/stats")
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_mcp_usage_stats(
    request: Request,
    _admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MCPUsageStatsResponse:
    now = datetime.now(timezone.utc)
    today = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    row = (
        await db.execute(
            select(
                func.count(MCPInvocation.id).label("total_calls"),
                func.count(MCPInvocation.id).filter(MCPInvocation.invoked_at >= today).label("calls_today"),
                func.count(MCPInvocation.id).filter(MCPInvocation.invoked_at >= week_ago).label("calls_week"),
                func.count(MCPInvocation.id).filter(MCPInvocation.invoked_at >= month_ago).label("calls_month"),
                func.count(MCPInvocation.id).filter(MCPInvocation.success.is_(True)).label("successful"),
                func.avg(MCPInvocation.duration_ms).label("avg_duration"),
                func.count(func.distinct(MCPInvocation.user_id)).label("unique_users"),
                func.count(func.distinct(MCPInvocation.mcp_api_key_id)).label("unique_keys"),
                func.count(MCPInvocation.id)
                .filter(MCPInvocation.tool_name == "search_jobs")
                .label("search_count"),
                func.avg(MCPInvocation.result_count)
                .filter(MCPInvocation.tool_name == "search_jobs")
                .label("avg_search_results"),
            )
        )
    ).one()
    total = int(row.total_calls or 0)
    return MCPUsageStatsResponse(
        total_calls=total,
        calls_today=int(row.calls_today or 0),
        calls_this_week=int(row.calls_week or 0),
        calls_this_month=int(row.calls_month or 0),
        success_rate=_percentage(int(row.successful or 0), total),
        average_duration_ms=round(float(row.avg_duration or 0), 2),
        unique_users=int(row.unique_users or 0),
        unique_keys=int(row.unique_keys or 0),
        search_count=int(row.search_count or 0),
        average_search_result_count=round(float(row.avg_search_results or 0), 2),
    )


@router.get("/tools")
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_mcp_tool_usage(
    request: Request,
    _admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MCPToolUsageResponse]:
    rows = (
        await db.execute(
            select(
                MCPInvocation.tool_name,
                func.count(MCPInvocation.id).label("total"),
                func.sum(case((MCPInvocation.success.is_(True), 1), else_=0)).label("successful"),
                func.avg(MCPInvocation.duration_ms).label("avg_duration"),
                func.avg(MCPInvocation.result_count).label("avg_results"),
            )
            .group_by(MCPInvocation.tool_name)
            .order_by(func.count(MCPInvocation.id).desc(), MCPInvocation.tool_name)
        )
    ).all()
    return [
        MCPToolUsageResponse(
            tool_name=row.tool_name,
            total_calls=int(row.total),
            successful_calls=int(row.successful or 0),
            failed_calls=int(row.total) - int(row.successful or 0),
            success_rate=_percentage(int(row.successful or 0), int(row.total)),
            average_duration_ms=round(float(row.avg_duration or 0), 2),
            average_result_count=None if row.avg_results is None else round(float(row.avg_results), 2),
        )
        for row in rows
    ]


@router.get("/daily")
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_mcp_daily_usage(
    request: Request,
    _admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> list[MCPDailyUsageResponse]:
    since = datetime.now(timezone.utc) - timedelta(days=days - 1)
    day_expr = func.date(MCPInvocation.invoked_at)
    rows = (
        await db.execute(
            select(
                day_expr.label("day"),
                func.count(MCPInvocation.id).label("total"),
                func.sum(case((MCPInvocation.success.is_(True), 1), else_=0)).label("successful"),
                func.count(func.distinct(MCPInvocation.user_id)).label("unique_users"),
            )
            .where(MCPInvocation.invoked_at >= since)
            .group_by(day_expr)
            .order_by(day_expr)
        )
    ).all()
    return [
        MCPDailyUsageResponse(
            date=row.day.isoformat() if hasattr(row.day, "isoformat") else str(row.day),
            total_calls=int(row.total),
            successful_calls=int(row.successful or 0),
            failed_calls=int(row.total) - int(row.successful or 0),
            unique_users=int(row.unique_users or 0),
        )
        for row in rows
    ]


@router.get("/events")
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_mcp_invocation_events(
    request: Request,
    _admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    tool: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    status: Literal["success", "failure"] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> AdminListResponse[MCPInvocationResponse]:
    conditions = []
    if tool:
        conditions.append(MCPInvocation.tool_name == tool)
    if status:
        conditions.append(MCPInvocation.success.is_(status == "success"))
    if date_from:
        conditions.append(
            MCPInvocation.invoked_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        )
    if date_to:
        conditions.append(
            MCPInvocation.invoked_at
            < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        )

    def _map(mcp_row) -> MCPInvocationResponse:
        return MCPInvocationResponse(
            id=mcp_row.id,
            user_id=mcp_row.user_id,
            mcp_key_id=mcp_row.mcp_api_key_id,
            tool_name=mcp_row.tool_name,
            called_at=mcp_row.invoked_at,
            success=mcp_row.success,
            duration_ms=mcp_row.duration_ms,
            job_id=mcp_row.job_id,
            result_count=mcp_row.result_count,
            error_category=mcp_row.error_category,
            metadata=mcp_row.metadata_,
        )

    return await paginate(
        db,
        base_query=select(MCPInvocation).where(*conditions),
        page=page,
        page_size=page_size,
        mapper=_map,
        order_by=(MCPInvocation.invoked_at.desc(),),
        count_stmt=select(func.count(MCPInvocation.id)).where(*conditions),
        scalars=True,
    )
