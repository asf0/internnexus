"""Admin click analytics routes."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.admin import (
    AdminListResponse,
    ClickStatsResponse,
    ClicksByUserResponse,
    DayClickStatsResponse,
    HourlyClicks,
    JobClickResponse,
    TopJobByClicks,
)
from app.auth.dependencies import AdminDep
from app.infra.db import get_db

from .shared import paginate_job_clicks
from app.models import Job, JobClick, User
from app.infra.rate_limiter import RATE_LIMITS, limiter

router = APIRouter()


async def _top_dimension(db: AsyncSession, column: Any) -> list[dict[str, Any]]:
    """Top 10 values for a nullable UTM dimension, bucketing NULL as "unknown"."""
    expr = func.coalesce(column, "unknown")
    result = await db.execute(
        select(expr.label("value"), func.count(JobClick.id).label("click_count"))
        .group_by(expr)
        .order_by(func.count(JobClick.id).desc())
        .limit(10)
    )
    return [{"value": row.value, "click_count": row.click_count} for row in result.all()]


def _fill_daily_series(
    now: datetime,
    days: int,
    rows: Sequence[Any],
    fields: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build a dense day series, defaulting missing days to zero."""
    row_map = {str(row.date): row for row in rows}
    series: list[dict[str, Any]] = []
    for i in range(days):
        key = str((now - timedelta(days=days - 1 - i)).date())
        row = row_map.get(key)
        entry: dict[str, Any] = {"date": key}
        for name, accessor in fields.items():
            entry[name] = int(accessor(row)) if row else 0
        series.append(entry)
    return series

# ============================================================================
# Click Tracking Endpoints
# ============================================================================


@router.get("/clicks/by-user")
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_clicks_by_user(
    request: Request,
    _admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100, description='Maximum number of users to return')] = 20,
) -> list[ClicksByUserResponse]:
    """Get click counts aggregated by user.

    Returns top users by click count, including anonymous clicks (null user).
    Joins JobClick with User to get user email and name.

    Args:
        request: FastAPI request object for rate limiting
        _admin: Authenticated admin user
        db: Database session
        limit: Maximum number of users to return (default 20)

    Returns:
        List of users with their click counts, ordered by click count descending
    """
    # Query clicks grouped by user with user info
    result = await db.execute(
        select(
            JobClick.user_id,
            User.email,
            User.name,
            func.count(JobClick.id).label("click_count"),
        )
        .outerjoin(User, JobClick.user_id == User.id)
        .group_by(JobClick.user_id, User.email, User.name)
        .order_by(func.count(JobClick.id).desc())
        .limit(limit)
    )
    rows = result.all()

    return [
        ClicksByUserResponse(
            user_id=row.user_id,
            email=row.email,
            name=row.name,
            click_count=row.click_count,
        )
        for row in rows
    ]


@router.get("/clicks/stats")
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_click_stats(
    request: Request,
    _admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClickStatsResponse:
    """Get click statistics overview.

    Returns total clicks, clicks for different time periods, and top 10 jobs by clicks.

    Args:
        request: FastAPI request object for rate limiting
        _admin: Authenticated admin user
        db: Database session

    Returns:
        ClickStatsResponse with click statistics
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    last_24h = now - timedelta(hours=24)

    counts_stmt = select(
        func.count(JobClick.id).label("total_clicks"),
        func.count(JobClick.id).filter(JobClick.clicked_at >= today_start).label("clicks_today"),
        func.count(JobClick.id).filter(JobClick.clicked_at >= week_ago).label("clicks_this_week"),
        func.count(JobClick.id).filter(JobClick.clicked_at >= month_ago).label("clicks_this_month"),
        func.count(JobClick.id)
        .filter(JobClick.user_id.isnot(None))
        .label("authenticated_clicks_total"),
        func.count(func.distinct(JobClick.user_id))
        .filter(JobClick.user_id.isnot(None))
        .label("unique_users_total"),
        func.count(func.distinct(JobClick.job_id)).label("unique_jobs_total"),
        func.count(JobClick.id).filter(JobClick.clicked_at >= last_24h).label("clicks_last_24h"),
    ).select_from(JobClick)
    counts = (await db.execute(counts_stmt)).one()

    total_clicks = counts.total_clicks or 0
    clicks_this_month = counts.clicks_this_month or 0
    anonymous_clicks_total = max(0, total_clicks - (counts.authenticated_clicks_total or 0))

    # 30-day average clicks/day
    avg_clicks_per_day_30d = round(clicks_this_month / 30.0, 2)

    # Top traffic dimensions
    top_sources = await _top_dimension(db, JobClick.utm_source)
    top_mediums = await _top_dimension(db, JobClick.utm_medium)
    top_campaigns = await _top_dimension(db, JobClick.utm_campaign)

    # Hourly clicks for today (0-23)
    hourly_today_result = await db.execute(
        select(
            extract("hour", JobClick.clicked_at).label("hour"),
            func.count(JobClick.id).label("clicks"),
        )
        .where(JobClick.clicked_at >= today_start)
        .group_by(extract("hour", JobClick.clicked_at))
        .order_by(extract("hour", JobClick.clicked_at))
    )
    hourly_today_rows = hourly_today_result.all()
    hourly_today_map = {int(row.hour): row.clicks for row in hourly_today_rows}
    clicks_by_hour_today = [
        HourlyClicks(hour=hour, clicks=hourly_today_map.get(hour, 0)) for hour in range(24)
    ]

    # 14-day breakdown with daily clicks and unique users
    day_breakdown_result = await db.execute(
        select(
            func.date(JobClick.clicked_at).label("date"),
            func.count(JobClick.id).label("clicks"),
            func.count(func.distinct(JobClick.user_id)).label("unique_users"),
        )
        .where(JobClick.clicked_at >= (now - timedelta(days=14)))
        .group_by(func.date(JobClick.clicked_at))
        .order_by(func.date(JobClick.clicked_at))
    )
    day_rows = day_breakdown_result.all()
    daily_breakdown_14d = _fill_daily_series(
        now,
        14,
        day_rows,
        {
            "clicks": lambda row: row.clicks,
            "unique_users": lambda row: row.unique_users,
        },
    )

    # Top 10 jobs by click count
    top_jobs_result = await db.execute(
        select(
            JobClick.job_id,
            Job.title,
            Job.company,
            func.count(JobClick.id).label("click_count"),
        )
        .join(Job, JobClick.job_id == Job.id)
        .group_by(JobClick.job_id, Job.title, Job.company)
        .order_by(func.count(JobClick.id).desc())
        .limit(10)
    )
    top_jobs = [
        {
            "job_id": str(row.job_id),
            "title": row.title,
            "company": row.company,
            "click_count": row.click_count,
        }
        for row in top_jobs_result.all()
    ]

    return ClickStatsResponse(
        total_clicks=total_clicks,
        clicks_today=counts.clicks_today or 0,
        clicks_this_week=counts.clicks_this_week or 0,
        clicks_this_month=clicks_this_month,
        authenticated_clicks_total=counts.authenticated_clicks_total or 0,
        anonymous_clicks_total=anonymous_clicks_total,
        unique_users_total=counts.unique_users_total or 0,
        unique_jobs_total=counts.unique_jobs_total or 0,
        clicks_last_24h=counts.clicks_last_24h or 0,
        avg_clicks_per_day_30d=avg_clicks_per_day_30d,
        top_sources=top_sources,
        top_mediums=top_mediums,
        top_campaigns=top_campaigns,
        clicks_by_hour_today=clicks_by_hour_today,
        daily_breakdown_14d=daily_breakdown_14d,
        top_jobs=top_jobs,
    )


@router.get("/clicks")
@limiter.limit(RATE_LIMITS["admin_read"])
async def list_clicks(
    request: Request,
    _admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    job_id: Annotated[UUID | None, Query()] = None,
) -> AdminListResponse[JobClickResponse]:
    """List recent clicks with pagination and optional job filter.

    Args:
        request: FastAPI request object for rate limiting
        _admin: Authenticated admin user
        db: Database session
        page: Page number (1-indexed)
        page_size: Number of items per page
        job_id: Optional filter by job ID

    Returns:
        Paginated list of job clicks with job title and company
    """
    # Build base query with join to get user info
    base_query = (
        select(JobClick, Job.title, Job.company, Job.apply_url, User.email, User.name)
        .join(Job, JobClick.job_id == Job.id)
        .outerjoin(User, JobClick.user_id == User.id)
        .order_by(JobClick.clicked_at.desc())
    )

    # Apply job filter if provided
    if job_id:
        base_query = base_query.where(JobClick.job_id == job_id)

    return await paginate_job_clicks(db, base_query, page=page, page_size=page_size)


@router.get("/clicks/by-day")
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_clicks_by_day(
    request: Request,
    _admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> list[dict[str, Any]]:
    """Get clicks grouped by day for the last N days.

    Fills in missing days with 0 clicks for complete time series.

    Args:
        request: FastAPI request object for rate limiting
        _admin: Authenticated admin user
        db: Database session
        days: Number of days to include (default 30, max 365)

    Returns:
        List of {date, clicks} dictionaries for each day
    """
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    # Query clicks grouped by date
    result = await db.execute(
        select(
            func.date(JobClick.clicked_at).label("date"),
            func.count(JobClick.id).label("clicks"),
            func.count(func.distinct(JobClick.user_id)).label("unique_users"),
            func.count(func.distinct(JobClick.job_id)).label("unique_jobs"),
        )
        .where(JobClick.clicked_at >= start_date)
        .group_by(func.date(JobClick.clicked_at))
        .order_by(func.date(JobClick.clicked_at))
    )
    rows = result.all()

    # Fill in missing days with 0 clicks
    return _fill_daily_series(
        now,
        days,
        rows,
        {
            "clicks": lambda row: row.clicks,
            "unique_users": lambda row: row.unique_users,
            "unique_jobs": lambda row: row.unique_jobs,
        },
    )


@router.get("/clicks/date/{date}", responses={400: {"description": "Bad request"}})
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_clicks_by_date(
    request: Request,
    date: str,  # Format: YYYY-MM-DD
    _admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DayClickStatsResponse:
    """Get detailed click statistics for a specific date.

    Returns total clicks, unique jobs/users, hourly breakdown, and top jobs
    for the specified date (UTC timezone).

    Args:
        request: FastAPI request object for rate limiting
        date: Date string in YYYY-MM-DD format
        _admin: Authenticated admin user
        db: Database session

    Returns:
        DayClickStatsResponse with detailed click statistics for the date

    Raises:
        HTTPException: 400 if date format is invalid
    """
    # Parse the date string
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD format.",
        )

    # Calculate start and end datetime for that date (UTC)
    start_datetime = datetime.combine(parsed_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_datetime = datetime.combine(parsed_date, datetime.max.time()).replace(tzinfo=timezone.utc)

    # Query total clicks for that date
    total_result = await db.execute(
        select(func.count(JobClick.id)).where(
            JobClick.clicked_at >= start_datetime,
            JobClick.clicked_at <= end_datetime,
        )
    )
    total_clicks = total_result.scalar() or 0

    # Calculate unique_jobs
    unique_jobs_result = await db.execute(
        select(func.count(func.distinct(JobClick.job_id))).where(
            JobClick.clicked_at >= start_datetime,
            JobClick.clicked_at <= end_datetime,
        )
    )
    unique_jobs = unique_jobs_result.scalar() or 0

    # Calculate unique_users (only logged-in users)
    unique_users_result = await db.execute(
        select(func.count(func.distinct(JobClick.user_id))).where(
            JobClick.clicked_at >= start_datetime,
            JobClick.clicked_at <= end_datetime,
            JobClick.user_id.isnot(None),
        )
    )
    unique_users = unique_users_result.scalar() or 0

    # Calculate anonymous_clicks
    anonymous_clicks_result = await db.execute(
        select(func.count(JobClick.id)).where(
            JobClick.clicked_at >= start_datetime,
            JobClick.clicked_at <= end_datetime,
            JobClick.user_id.is_(None),
        )
    )
    anonymous_clicks = anonymous_clicks_result.scalar() or 0

    # Calculate clicks_by_hour (group by hour, return hours 0-23 with counts)
    hourly_result = await db.execute(
        select(
            extract("hour", JobClick.clicked_at).label("hour"),
            func.count(JobClick.id).label("clicks"),
        )
        .where(
            JobClick.clicked_at >= start_datetime,
            JobClick.clicked_at <= end_datetime,
        )
        .group_by(extract("hour", JobClick.clicked_at))
    )
    hourly_rows = hourly_result.all()

    # Create a map of hour to clicks
    clicks_by_hour_map = {int(row.hour): row.clicks for row in hourly_rows}

    # Build clicks_by_hour list with all 24 hours (0-23)
    clicks_by_hour = [
        HourlyClicks(hour=hour, clicks=clicks_by_hour_map.get(hour, 0)) for hour in range(24)
    ]

    # Get top_jobs: join with Job, group by job, get top 10
    top_jobs_result = await db.execute(
        select(
            JobClick.job_id,
            Job.title,
            Job.company,
            Job.apply_url,
            func.count(JobClick.id).label("click_count"),
        )
        .join(Job, JobClick.job_id == Job.id)
        .where(
            JobClick.clicked_at >= start_datetime,
            JobClick.clicked_at <= end_datetime,
        )
        .group_by(JobClick.job_id, Job.title, Job.company, Job.apply_url)
        .order_by(func.count(JobClick.id).desc())
        .limit(10)
    )
    top_jobs_rows = top_jobs_result.all()

    top_jobs = [
        TopJobByClicks(
            job_id=row.job_id,
            title=row.title,
            company=row.company,
            apply_url=row.apply_url,
            click_count=row.click_count,
        )
        for row in top_jobs_rows
    ]

    return DayClickStatsResponse(
        date=date,
        total_clicks=total_clicks,
        unique_jobs=unique_jobs,
        unique_users=unique_users,
        anonymous_clicks=anonymous_clicks,
        clicks_by_hour=clicks_by_hour,
        top_jobs=top_jobs,
    )
