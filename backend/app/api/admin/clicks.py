"""Admin click analytics routes."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_schemas import (
    AdminListResponse,
    ClicksByUserResponse,
    ClickStatsResponse,
    DayClickStatsResponse,
    HourlyClicks,
    JobClickResponse,
    TopJobByClicks,
)
from app.auth.dependencies import AdminDep
from app.db import get_db
from app.models import Job, JobClick, User
from app.rate_limiter import RATE_LIMITS, limiter

router = APIRouter()

# ============================================================================
# Click Tracking Endpoints
# ============================================================================


@router.get("/clicks/by-user", response_model=list[ClicksByUserResponse])
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_clicks_by_user(
    request: Request,
    _admin: AdminDep,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of users to return"),
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


@router.get("/clicks/stats", response_model=ClickStatsResponse)
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_click_stats(
    request: Request,
    _admin: AdminDep,
    db: AsyncSession = Depends(get_db),
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

    # Total clicks
    total_result = await db.execute(select(func.count(JobClick.id)))
    total_clicks = total_result.scalar() or 0

    # Clicks today
    today_result = await db.execute(
        select(func.count(JobClick.id)).where(JobClick.clicked_at >= today_start)
    )
    clicks_today = today_result.scalar() or 0

    # Clicks this week (last 7 days)
    week_result = await db.execute(
        select(func.count(JobClick.id)).where(JobClick.clicked_at >= week_ago)
    )
    clicks_this_week = week_result.scalar() or 0

    # Clicks this month (last 30 days)
    month_result = await db.execute(
        select(func.count(JobClick.id)).where(JobClick.clicked_at >= month_ago)
    )
    clicks_this_month = month_result.scalar() or 0

    # Authenticated vs anonymous totals
    authenticated_result = await db.execute(
        select(func.count(JobClick.id)).where(JobClick.user_id.isnot(None))
    )
    authenticated_clicks_total = authenticated_result.scalar() or 0
    anonymous_clicks_total = max(0, total_clicks - authenticated_clicks_total)

    # Unique users/jobs overall
    unique_users_result = await db.execute(
        select(func.count(func.distinct(JobClick.user_id))).where(JobClick.user_id.isnot(None))
    )
    unique_users_total = unique_users_result.scalar() or 0

    unique_jobs_result = await db.execute(select(func.count(func.distinct(JobClick.job_id))))
    unique_jobs_total = unique_jobs_result.scalar() or 0

    # Last 24h clicks
    last_24h = now - timedelta(hours=24)
    last_24h_result = await db.execute(
        select(func.count(JobClick.id)).where(JobClick.clicked_at >= last_24h)
    )
    clicks_last_24h = last_24h_result.scalar() or 0

    # 30-day average clicks/day
    avg_clicks_per_day_30d = round(clicks_this_month / 30.0, 2)

    # Top traffic dimensions
    source_expr = func.coalesce(JobClick.utm_source, "unknown")
    top_sources_result = await db.execute(
        select(
            source_expr.label("value"),
            func.count(JobClick.id).label("click_count"),
        )
        .group_by(source_expr)
        .order_by(func.count(JobClick.id).desc())
        .limit(10)
    )
    top_sources = [
        {"value": row.value, "click_count": row.click_count} for row in top_sources_result.all()
    ]

    medium_expr = func.coalesce(JobClick.utm_medium, "unknown")
    top_mediums_result = await db.execute(
        select(
            medium_expr.label("value"),
            func.count(JobClick.id).label("click_count"),
        )
        .group_by(medium_expr)
        .order_by(func.count(JobClick.id).desc())
        .limit(10)
    )
    top_mediums = [
        {"value": row.value, "click_count": row.click_count} for row in top_mediums_result.all()
    ]

    campaign_expr = func.coalesce(JobClick.utm_campaign, "unknown")
    top_campaigns_result = await db.execute(
        select(
            campaign_expr.label("value"),
            func.count(JobClick.id).label("click_count"),
        )
        .group_by(campaign_expr)
        .order_by(func.count(JobClick.id).desc())
        .limit(10)
    )
    top_campaigns = [
        {"value": row.value, "click_count": row.click_count} for row in top_campaigns_result.all()
    ]

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
    day_map = {str(row.date): row for row in day_rows}
    daily_breakdown_14d: list[dict[str, Any]] = []
    for i in range(14):
        day = (now - timedelta(days=13 - i)).date()
        key = str(day)
        row = day_map.get(key)
        daily_breakdown_14d.append(
            {
                "date": key,
                "clicks": row.clicks if row else 0,
                "unique_users": int(row.unique_users) if row else 0,
            }
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
        clicks_today=clicks_today,
        clicks_this_week=clicks_this_week,
        clicks_this_month=clicks_this_month,
        authenticated_clicks_total=authenticated_clicks_total,
        anonymous_clicks_total=anonymous_clicks_total,
        unique_users_total=unique_users_total,
        unique_jobs_total=unique_jobs_total,
        clicks_last_24h=clicks_last_24h,
        avg_clicks_per_day_30d=avg_clicks_per_day_30d,
        top_sources=top_sources,
        top_mediums=top_mediums,
        top_campaigns=top_campaigns,
        clicks_by_hour_today=clicks_by_hour_today,
        daily_breakdown_14d=daily_breakdown_14d,
        top_jobs=top_jobs,
    )


@router.get("/clicks", response_model=AdminListResponse[JobClickResponse])
@limiter.limit(RATE_LIMITS["admin_read"])
async def list_clicks(
    request: Request,
    _admin: AdminDep,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    job_id: UUID | None = Query(None),
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

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    paginated_query = base_query.offset(offset).limit(page_size)

    result = await db.execute(paginated_query)
    rows = result.all()

    # Build response items
    items = [
        JobClickResponse(
            id=row.JobClick.id,
            job_id=row.JobClick.job_id,
            job_title=row.title,
            company=row.company,
            apply_url=row.apply_url,
            user_id=row.JobClick.user_id,
            user_email=row.email,
            user_name=row.name,
            clicked_at=row.JobClick.clicked_at,
            utm_source=row.JobClick.utm_source,
            utm_medium=row.JobClick.utm_medium,
            utm_campaign=row.JobClick.utm_campaign,
        )
        for row in rows
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return AdminListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/clicks/by-day")
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_clicks_by_day(
    request: Request,
    _admin: AdminDep,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
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

    # Create a map of date to clicks
    clicks_by_date = {str(row.date): row for row in rows}

    # Fill in missing days with 0 clicks
    response = []
    for i in range(days):
        date = (now - timedelta(days=days - 1 - i)).date()
        date_str = str(date)
        row = clicks_by_date.get(date_str)
        response.append(
            {
                "date": date_str,
                "clicks": row.clicks if row else 0,
                "unique_users": int(row.unique_users) if row else 0,
                "unique_jobs": int(row.unique_jobs) if row else 0,
            }
        )

    return response


@router.get("/clicks/date/{date}", response_model=DayClickStatsResponse)
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_clicks_by_date(
    request: Request,
    date: str,  # Format: YYYY-MM-DD
    _admin: AdminDep,
    db: AsyncSession = Depends(get_db),
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
