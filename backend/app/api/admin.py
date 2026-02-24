"""Admin API endpoints for managing jobs and system operations."""

from __future__ import annotations

import csv
import hashlib
import io
import logging
import math
import typing
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.admin_schemas import (
    AdminJobBulkRequest,
    AdminJobCreateRequest,
    AdminJobResponse,
    AdminJobUpdateRequest,
    AdminListResponse,
    AdminUserResponse,
    ClicksByUserResponse,
    ClickStatsResponse,
    DayClickStatsResponse,
    HourlyClicks,
    JobClickResponse,
    PipelineRunResponse,
    TopJobByClicks,
    UserCreateRequest,
    UserNotesUpdateRequest,
)
from app.auth.dependencies import AdminDep, SuperAdminDep
from app.auth.jwt import get_password_hash
from app.db import get_db
from app.models import (
    Account,
    Admin,
    AdminRole,
    Job,
    JobClick,
    JobSource,
    JobType,
    PipelineRun,
    PipelineRunStatus,
    User,
    WorkMode,
)
from app.rate_limiter import RATE_LIMITS, limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/jobs", response_model=AdminListResponse[AdminJobResponse])
@limiter.limit(RATE_LIMITS["admin"])
async def list_jobs(
    request: Request,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search in title and company"),
    company: str | None = Query(None, description="Filter by company name"),
    category: str | None = Query(None, description="Filter by job category"),
    is_active: bool | None = Query(None, description="Filter by active status"),
) -> AdminListResponse[AdminJobResponse]:
    """List all jobs with pagination and filters for admin dashboard.

    Includes click count for each job via LEFT JOIN with job_clicks table.

    Args:
        request: FastAPI request object for rate limiting
        admin: Authenticated admin user
        db: Database session
        page: Page number (1-indexed)
        page_size: Number of items per page
        search: Optional search term for title and company (case-insensitive)
        company: Optional filter by company name
        category: Optional filter by job category
        is_active: Optional filter by active status

    Returns:
        Paginated list of jobs with click counts
    """
    # Build base query with click count subquery
    click_count_subquery = (
        select(JobClick.job_id, func.count(JobClick.id).label("click_count"))
        .group_by(JobClick.job_id)
        .subquery()
    )

    # Main query with LEFT JOIN to click counts
    query = select(
        Job,
        func.coalesce(click_count_subquery.c.click_count, 0).label("click_count"),
    ).outerjoin(click_count_subquery, Job.id == click_count_subquery.c.job_id)

    # Apply filters
    if search:
        search_pattern = f"%{search.lower()}%"
        query = query.where(
            (func.lower(Job.title).ilike(search_pattern))
            | (func.lower(Job.company).ilike(search_pattern))
        )

    if company:
        query = query.where(func.lower(Job.company) == company.lower())

    if category:
        query = query.where(Job.job_category == category)

    if is_active is not None:
        query = query.where(Job.is_active == is_active)

    # Get total count for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Job.last_seen.desc()).offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    rows = result.all()

    # Build response items
    items = []
    for row in rows:
        job = row[0]
        click_count = row[1]
        items.append(
            AdminJobResponse(
                id=job.id,
                source=job.source.value if job.source else None,
                title=job.title,
                company=job.company,
                location=job.location,
                city=job.city,
                state=job.state,
                country=job.country,
                apply_url=job.apply_url,
                description_text=job.description_text,
                job_category=job.job_category,
                job_type=job.job_type.value if job.job_type else None,
                work_mode=job.work_mode.value if job.work_mode else None,
                posted_at=job.posted_at,
                is_active=job.is_active,
                click_count=click_count,
                created_at=job.last_seen,
            )
        )

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return AdminListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/jobs/stats")
@limiter.limit(RATE_LIMITS["admin"])
async def get_job_stats(
    request: Request,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get job statistics for admin dashboard.

    Args:
        request: FastAPI request object for rate limiting
        admin: Authenticated admin user
        db: Database session

    Returns:
        Dictionary with job statistics including totals and breakdown by category
    """
    # Total jobs
    total_result = await db.execute(select(func.count()).select_from(Job))
    total_jobs = total_result.scalar() or 0

    # Active jobs
    active_result = await db.execute(
        select(func.count()).select_from(Job).where(Job.is_active == True)
    )
    active_jobs = active_result.scalar() or 0

    # Total companies (distinct)
    companies_result = await db.execute(
        select(func.count(func.distinct(Job.company))).select_from(Job)
    )
    total_companies = companies_result.scalar() or 0

    # Jobs by category
    category_result = await db.execute(
        select(Job.job_category, func.count(Job.id).label("count"))
        .where(Job.job_category.isnot(None))
        .group_by(Job.job_category)
        .order_by(func.count(Job.id).desc())
    )
    category_rows = category_result.all()
    jobs_by_category = {row.job_category: row.count for row in category_rows if row.job_category}

    return {
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "total_companies": total_companies,
        "jobs_by_category": jobs_by_category,
    }


@router.get("/jobs/{job_id}", response_model=AdminJobResponse)
@limiter.limit(RATE_LIMITS["admin"])
async def get_job(
    request: Request,
    job_id: UUID,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
    """Get a single job by ID with click count.

    Args:
        request: FastAPI request object for rate limiting
        job_id: UUID of the job to retrieve
        admin: Authenticated admin user
        db: Database session

    Returns:
        Job details with click count

    Raises:
        HTTPException: 404 if job not found
    """
    # Query job with click count
    click_count_subquery = (
        select(JobClick.job_id, func.count(JobClick.id).label("click_count"))
        .where(JobClick.job_id == job_id)
        .group_by(JobClick.job_id)
        .subquery()
    )

    query = (
        select(
            Job,
            func.coalesce(click_count_subquery.c.click_count, 0).label("click_count"),
        )
        .outerjoin(click_count_subquery, Job.id == click_count_subquery.c.job_id)
        .where(Job.id == job_id)
    )

    result = await db.execute(query)
    row = result.first()

    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")

    job = row[0]
    click_count = row[1]

    return AdminJobResponse(
        id=job.id,
        source=job.source.value if job.source else None,
        title=job.title,
        company=job.company,
        location=job.location,
        city=job.city,
        state=job.state,
        country=job.country,
        apply_url=job.apply_url,
        description_text=job.description_text,
        job_category=job.job_category,
        job_type=job.job_type.value if job.job_type else None,
        work_mode=job.work_mode.value if job.work_mode else None,
        posted_at=job.posted_at,
        is_active=job.is_active,
        click_count=click_count,
        created_at=job.last_seen,
    )


@router.patch("/jobs/{job_id}", response_model=AdminJobResponse)
@limiter.limit(RATE_LIMITS["admin"])
async def update_job(
    request: Request,
    job_id: UUID,
    update_data: AdminJobUpdateRequest,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
    """Update a job's details.

    Only updates fields that are provided (not None).

    Args:
        request: FastAPI request object for rate limiting
        job_id: UUID of the job to update
        update_data: Fields to update
        admin: Authenticated admin user
        db: Database session

    Returns:
        Updated job details with click count

    Raises:
        HTTPException: 404 if job not found
    """
    # Fetch the job
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update only provided fields
    update_fields = update_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(job, field, value)

    await db.commit()
    await db.refresh(job)

    # Get click count
    click_result = await db.execute(
        select(func.count(JobClick.id)).where(JobClick.job_id == job_id)
    )
    click_count = click_result.scalar() or 0

    return AdminJobResponse(
        id=job.id,
        source=job.source.value if job.source else None,
        title=job.title,
        company=job.company,
        location=job.location,
        city=job.city,
        state=job.state,
        country=job.country,
        apply_url=job.apply_url,
        description_text=job.description_text,
        job_category=job.job_category,
        job_type=job.job_type.value if job.job_type else None,
        work_mode=job.work_mode.value if job.work_mode else None,
        posted_at=job.posted_at,
        is_active=job.is_active,
        click_count=click_count,
        created_at=job.last_seen,
    )


@router.delete("/jobs/{job_id}")
@limiter.limit(RATE_LIMITS["admin"])
async def delete_job(
    request: Request,
    job_id: UUID,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Soft delete a job by setting is_active to False.

    Args:
        request: FastAPI request object for rate limiting
        job_id: UUID of the job to deactivate
        admin: Authenticated admin user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if job not found
    """
    # Fetch the job
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Soft delete
    job.is_active = False
    await db.commit()

    return {"message": "Job deactivated"}


@router.post("/jobs", response_model=AdminJobResponse, status_code=201)
@limiter.limit(RATE_LIMITS["admin"])
async def create_job(
    request: Request,
    data: AdminJobCreateRequest,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
    """Create a new job manually via admin interface.

    Generates a unique fingerprint from title+company+apply_url and sets
    source to 'manual'.

    Args:
        request: FastAPI request object for rate limiting
        data: Job creation request with required fields
        admin: Authenticated admin user
        db: Database session

    Returns:
        Created job details

    Raises:
        HTTPException: 400 if fingerprint already exists (duplicate job)
    """
    # Generate fingerprint
    fingerprint = hashlib.sha256(
        f"{data.title}{data.company}{data.apply_url}".encode()
    ).hexdigest()[:64]

    # Check for duplicate fingerprint
    existing_result = await db.execute(select(Job).where(Job.fingerprint == fingerprint))
    existing_job = existing_result.scalar_one_or_none()

    if existing_job:
        raise HTTPException(
            status_code=400, detail="Job with this title, company, and URL already exists"
        )

    # Parse optional enum fields
    job_type = None
    if data.job_type:
        try:
            job_type = JobType(data.job_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid job_type. Must be one of: {[t.value for t in JobType]}",
            )

    work_mode = None
    if data.work_mode:
        try:
            work_mode = WorkMode(data.work_mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid work_mode. Must be one of: {[w.value for w in WorkMode]}",
            )

    # Create job
    new_job = Job(
        fingerprint=fingerprint,
        source=JobSource.manual,
        title=data.title,
        company=data.company,
        location=data.location,
        apply_url=data.apply_url,
        description_text=data.description_text,
        job_category=data.job_category,
        job_type=job_type,
        work_mode=work_mode,
        posted_at=data.posted_at or datetime.now(timezone.utc),
        is_active=True,
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    return AdminJobResponse(
        id=new_job.id,
        source=new_job.source.value,
        title=new_job.title,
        company=new_job.company,
        location=new_job.location,
        city=new_job.city,
        state=new_job.state,
        country=new_job.country,
        apply_url=new_job.apply_url,
        description_text=new_job.description_text,
        job_category=new_job.job_category,
        job_type=new_job.job_type.value if new_job.job_type else None,
        work_mode=new_job.work_mode.value if new_job.work_mode else None,
        posted_at=new_job.posted_at,
        is_active=new_job.is_active,
        click_count=0,
        created_at=new_job.last_seen,
    )


@router.delete("/jobs/{job_id}/hard")
@limiter.limit(RATE_LIMITS["admin"])
async def hard_delete_job(
    request: Request,
    job_id: UUID,
    super_admin: SuperAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Permanently delete a job from the database.

    Only allows hard delete if job is already soft-deleted (is_active = False).
    Only super admins can hard delete jobs.

    Args:
        request: FastAPI request object for rate limiting
        job_id: UUID of the job to permanently delete
        super_admin: Authenticated super admin user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if job not found, 400 if job is still active
    """
    # Fetch the job
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check if job is soft-deleted
    if job.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot hard delete an active job. Soft delete first.",
        )

    # Hard delete
    await db.delete(job)
    await db.commit()

    return {"message": "Job permanently deleted"}


@router.post("/jobs/bulk")
@limiter.limit(RATE_LIMITS["admin"])
async def bulk_job_action(
    request: Request,
    data: AdminJobBulkRequest,
    super_admin: SuperAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    """Perform bulk actions on multiple jobs.

    Supported actions: activate, deactivate, delete (soft delete).
    Only super admins can perform bulk actions.

    Args:
        request: FastAPI request object for rate limiting
        data: Bulk action request with job_ids and action
        super_admin: Authenticated super admin user
        db: Database session

    Returns:
        Count of affected jobs

    Raises:
        HTTPException: 400 if invalid action
    """
    # Validate action
    valid_actions = ["activate", "deactivate", "delete"]
    if data.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Must be one of: {valid_actions}",
        )

    # Determine new is_active value
    new_is_active = data.action == "activate"

    # Update jobs
    result = await db.execute(select(Job).where(Job.id.in_(data.job_ids)))
    jobs = result.scalars().all()

    for job in jobs:
        job.is_active = new_is_active

    await db.commit()

    return {"affected_count": len(jobs), "action": data.action}


# ============================================================================
# User Management Endpoints
# ============================================================================


class GrantAdminRequest(BaseModel):
    """Schema for granting admin access request."""

    notes: str | None = None
    role: str = "admin"


@router.get("/users", response_model=AdminListResponse[AdminUserResponse])
@limiter.limit(RATE_LIMITS["admin"])
async def list_users(
    request: Request,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search in email and name"),
    is_admin: bool | None = Query(None, description="Filter by admin status"),
) -> AdminListResponse[AdminUserResponse]:
    """List users with pagination, search, and admin filter.

    Args:
        request: FastAPI request object for rate limiting
        admin: Authenticated admin user
        db: Database session
        page: Page number (1-indexed)
        page_size: Number of items per page
        search: Optional search term for email and name (case-insensitive)
        is_admin: Optional filter by admin status

    Returns:
        Paginated list of users with admin role and provider info
    """
    # Build base query with relationships
    query = (
        select(User)
        .options(
            selectinload(User.admin),
            selectinload(User.accounts),
        )
        .order_by(User.created_at.desc())
    )

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                User.email.ilike(search_pattern),
                User.name.ilike(search_pattern),
            )
        )

    # Apply admin filter
    if is_admin is not None:
        admin_exists = select(Admin).where(Admin.user_id == User.id).exists()
        if is_admin:
            query = query.where(admin_exists)
        else:
            query = query.where(~admin_exists)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()

    # Build response items
    items = []
    for user in users:
        admin_role = None
        if user.admin:
            admin_role = user.admin.role.value

        provider = None
        if user.accounts:
            provider = user.accounts[0].provider

        items.append(
            AdminUserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                is_active=not user.is_deleted,
                created_at=user.created_at,
                has_password=user.hashed_password is not None,
                admin_role=admin_role,
                provider=provider,
            )
        )

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return AdminListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/users/{user_id}", response_model=AdminUserResponse)
@limiter.limit(RATE_LIMITS["admin"])
async def get_user(
    request: Request,
    user_id: UUID,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
) -> AdminUserResponse:
    """Get a single user by ID.

    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to retrieve
        admin: Authenticated admin user
        db: Database session

    Returns:
        User details with admin role and provider info

    Raises:
        HTTPException: 404 if user not found
    """
    query = (
        select(User)
        .options(
            selectinload(User.admin),
            selectinload(User.accounts),
        )
        .where(User.id == user_id)
    )

    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    admin_role = None
    if user.admin:
        admin_role = user.admin.role.value

    provider = None
    if user.accounts:
        provider = user.accounts[0].provider

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=not user.is_deleted,
        created_at=user.created_at,
        has_password=user.hashed_password is not None,
        admin_role=admin_role,
        provider=provider,
    )


@router.post("/users/{user_id}/grant-admin")
@limiter.limit(RATE_LIMITS["admin"])
async def grant_admin(
    request: Request,
    user_id: UUID,
    data: GrantAdminRequest,
    super_admin: SuperAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Grant admin access to a user. Only super admins can grant admin access.

    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to grant admin access
        data: Request body with optional notes and role
        super_admin: Authenticated super admin user
        db: Database session

    Returns:
        Success message with granted role

    Raises:
        HTTPException: 404 if user not found, 400 if invalid role
    """
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate role
    try:
        role = AdminRole(data.role)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {[r.value for r in AdminRole]}",
        )

    # Check if admin record already exists
    admin_result = await db.execute(select(Admin).where(Admin.user_id == user_id))
    existing_admin = admin_result.scalar_one_or_none()

    if existing_admin:
        # Update existing admin record
        existing_admin.role = role
        existing_admin.granted_by = super_admin.user_id
        existing_admin.granted_at = datetime.now(timezone.utc)
        if data.notes is not None:
            existing_admin.notes = data.notes
    else:
        # Create new admin record
        new_admin = Admin(
            user_id=user_id,
            role=role,
            granted_by=super_admin.user_id,
            notes=data.notes,
        )
        db.add(new_admin)

    await db.commit()

    return {"message": "Admin access granted", "role": role.value}


@router.delete("/users/{user_id}/revoke-admin")
@limiter.limit(RATE_LIMITS["admin"])
async def revoke_admin(
    request: Request,
    user_id: UUID,
    super_admin: SuperAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Revoke admin access from a user. Only super admins can revoke admin access.

    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to revoke admin access
        super_admin: Authenticated super admin user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if user is not an admin, 400 if trying to revoke own access
    """
    # Check if admin record exists
    admin_result = await db.execute(select(Admin).where(Admin.user_id == user_id))
    admin = admin_result.scalar_one_or_none()

    if not admin:
        raise HTTPException(status_code=404, detail="User is not an admin")

    # Prevent self-revocation
    if admin.user_id == super_admin.user_id:
        raise HTTPException(status_code=400, detail="Cannot revoke your own admin access")

    await db.delete(admin)
    await db.commit()

    return {"message": "Admin access revoked"}


@router.post("/users/{user_id}/deactivate")
@limiter.limit(RATE_LIMITS["admin"])
async def deactivate_user(
    request: Request,
    user_id: UUID,
    super_admin: SuperAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Deactivate a user account. Only super admins can deactivate users.

    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to deactivate
        super_admin: Authenticated super admin user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if user not found, 400 if trying to deactivate self
    """
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-deactivation
    if user.id == super_admin.user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    # Deactivate user
    user.is_deleted = True
    user.deleted_at = datetime.now(timezone.utc)

    await db.commit()

    return {"message": "User deactivated"}


@router.post("/users/{user_id}/reactivate")
@limiter.limit(RATE_LIMITS["admin"])
async def reactivate_user(
    request: Request,
    user_id: UUID,
    super_admin: SuperAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Reactivate a user account. Only super admins can reactivate users.

    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to reactivate
        super_admin: Authenticated super admin user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if user not found
    """
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Reactivate user
    user.is_deleted = False
    user.deleted_at = None

    await db.commit()

    return {"message": "User reactivated"}


@router.post("/users", response_model=AdminUserResponse, status_code=201)
@limiter.limit(RATE_LIMITS["admin"])
async def create_user(
    request: Request,
    data: UserCreateRequest,
    super_admin: SuperAdminDep,
    db: AsyncSession = Depends(get_db),
) -> AdminUserResponse:
    """Create a new user with email and password. Only super admins can create users.

    Args:
        request: FastAPI request object for rate limiting
        data: User creation request with email, password, and optional name
        super_admin: Authenticated super admin user
        db: Database session

    Returns:
        Created user details

    Raises:
        HTTPException: 400 if email already exists
    """
    # Check if email already exists
    existing_result = await db.execute(select(User).where(User.email == data.email))
    existing_user = existing_result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password and create user
    hashed_password = get_password_hash(data.password)
    new_user = User(
        email=data.email,
        hashed_password=hashed_password,
        name=data.name,
        email_verified=False,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return AdminUserResponse(
        id=new_user.id,
        email=new_user.email,
        name=new_user.name,
        is_active=not new_user.is_deleted,
        created_at=new_user.created_at,
        has_password=new_user.hashed_password is not None,
        admin_role=None,
        provider=None,
    )


@router.delete("/users/{user_id}/hard")
@limiter.limit(RATE_LIMITS["admin"])
async def hard_delete_user(
    request: Request,
    user_id: UUID,
    super_admin: SuperAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Permanently delete a user from the database. Only super admins can hard delete users.

    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to delete
        super_admin: Authenticated super admin user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if user not found, 400 if trying to delete self
    """
    # Prevent self-deletion
    if user_id == super_admin.user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Hard delete user
    await db.delete(user)
    await db.commit()

    return {"message": "User permanently deleted"}


@router.post("/users/{user_id}/reset-password")
@limiter.limit(RATE_LIMITS["admin"])
async def reset_user_password(
    request: Request,
    user_id: UUID,
    super_admin: SuperAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Initiate password reset for a user. Only super admins can reset passwords.

    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to reset password for
        super_admin: Authenticated super admin user
        db: Database session

    Returns:
        Success message (placeholder)

    Raises:
        HTTPException: 404 if user not found
    """
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # TODO: Implement email sending for password reset
    logger.info(f"Password reset requested for user {user_id} by super admin {super_admin.user_id}")

    return {"message": "Password reset email sent (placeholder)"}


@router.get("/users/{user_id}/clicks", response_model=AdminListResponse[JobClickResponse])
@limiter.limit(RATE_LIMITS["admin"])
async def get_user_clicks(
    request: Request,
    user_id: UUID,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> AdminListResponse[JobClickResponse]:
    """Get paginated list of job clicks for a specific user.

    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to get clicks for
        admin: Authenticated admin user
        db: Database session
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Paginated list of job clicks with job title and company

    Raises:
        HTTPException: 404 if user not found
    """
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Build base query with join to get user info
    base_query = (
        select(JobClick, Job.title, Job.company, User.email, User.name)
        .join(Job, JobClick.job_id == Job.id)
        .outerjoin(User, JobClick.user_id == User.id)
        .where(JobClick.user_id == user_id)
        .order_by(JobClick.clicked_at.desc())
    )

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


@router.patch("/users/{user_id}/notes")
@limiter.limit(RATE_LIMITS["admin"])
async def update_user_notes(
    request: Request,
    user_id: UUID,
    data: UserNotesUpdateRequest,
    super_admin: SuperAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Update notes for a user. Only super admins can update user notes.

    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to update notes for
        data: Request body with notes (can be null to clear)
        super_admin: Authenticated super admin user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if user not found
    """
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update notes
    user.notes = data.notes
    await db.commit()

    return {"message": "User notes updated"}


@router.get("/users/export")
@limiter.limit(RATE_LIMITS["admin"])
async def export_users_csv(
    request: Request,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export all users as a CSV file.

    Args:
        request: FastAPI request object for rate limiting
        admin: Authenticated admin user
        db: Database session

    Returns:
        StreamingResponse with CSV content for download
    """
    # Query all users with admin and account relationships
    query = (
        select(User)
        .options(
            selectinload(User.admin),
            selectinload(User.accounts),
        )
        .order_by(User.created_at.desc())
    )

    result = await db.execute(query)
    users = result.scalars().all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id",
            "email",
            "name",
            "is_active",
            "has_password",
            "admin_role",
            "provider",
            "created_at",
            "notes",
        ],
    )
    writer.writeheader()

    for user in users:
        admin_role = None
        if user.admin:
            admin_role = user.admin.role.value

        provider = None
        if user.accounts:
            provider = user.accounts[0].provider

        writer.writerow(
            {
                "id": str(user.id),
                "email": user.email,
                "name": user.name or "",
                "is_active": str(not user.is_deleted),
                "has_password": str(user.hashed_password is not None),
                "admin_role": admin_role or "",
                "provider": provider or "",
                "created_at": user.created_at.isoformat() if user.created_at else "",
                "notes": user.notes or "",
            }
        )

    # Reset buffer position
    output.seek(0)

    # Create streaming response
    def iter_csv() -> typing.Iterator[str]:
        yield output.getvalue()

    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=users_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        },
    )


# ============================================================================
# Pipeline Run Endpoints
# ============================================================================


@router.get("/pipeline-runs/stats")
@limiter.limit(RATE_LIMITS["admin"])
async def get_pipeline_stats(
    request: Request,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get pipeline run statistics.

    Args:
        request: FastAPI request object for rate limiting
        admin: Authenticated admin user
        db: Database session

    Returns:
        Dictionary with pipeline statistics
    """
    # Total runs
    total_result = await db.execute(select(func.count()).select_from(PipelineRun))
    total_runs = total_result.scalar() or 0

    # Completed runs
    completed_result = await db.execute(
        select(func.count())
        .select_from(PipelineRun)
        .where(PipelineRun.status == PipelineRunStatus.completed)
    )
    completed = completed_result.scalar() or 0

    # Failed runs
    failed_result = await db.execute(
        select(func.count())
        .select_from(PipelineRun)
        .where(PipelineRun.status == PipelineRunStatus.failed)
    )
    failed = failed_result.scalar() or 0

    # Running runs
    running_result = await db.execute(
        select(func.count())
        .select_from(PipelineRun)
        .where(PipelineRun.status == PipelineRunStatus.running)
    )
    running = running_result.scalar() or 0

    # Last success
    last_success_result = await db.execute(
        select(PipelineRun.completed_at)
        .where(PipelineRun.status == PipelineRunStatus.completed)
        .order_by(PipelineRun.completed_at.desc())
        .limit(1)
    )
    last_success = last_success_result.scalar_one_or_none()

    # Last failure
    last_failure_result = await db.execute(
        select(PipelineRun.completed_at)
        .where(PipelineRun.status == PipelineRunStatus.failed)
        .order_by(PipelineRun.completed_at.desc())
        .limit(1)
    )
    last_failure = last_failure_result.scalar_one_or_none()

    return {
        "total_runs": total_runs,
        "completed": completed,
        "failed": failed,
        "running": running,
        "last_success": last_success,
        "last_failure": last_failure,
    }


@router.get("/pipeline-runs/latest", response_model=PipelineRunResponse | None)
@limiter.limit(RATE_LIMITS["admin"])
async def get_latest_pipeline_run(
    request: Request,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
) -> PipelineRunResponse | None:
    """Get the most recent pipeline run.

    Args:
        request: FastAPI request object for rate limiting
        admin: Authenticated admin user
        db: Database session

    Returns:
        Most recent pipeline run or None if no runs exist
    """
    result = await db.execute(select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(1))
    run = result.scalar_one_or_none()

    if run is None:
        return None

    return PipelineRunResponse.model_validate(run)


@router.get("/pipeline-runs", response_model=AdminListResponse[PipelineRunResponse])
@limiter.limit(RATE_LIMITS["admin"])
async def list_pipeline_runs(
    request: Request,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status (running, completed, failed)"),
) -> AdminListResponse[PipelineRunResponse]:
    """List pipeline runs with optional status filter.

    Args:
        request: FastAPI request object for rate limiting
        admin: Authenticated admin user
        db: Database session
        page: Page number (1-indexed)
        page_size: Number of items per page
        status: Optional status filter (running, completed, failed)

    Returns:
        Paginated list of pipeline runs
    """
    # Build base query
    query = select(PipelineRun)

    # Apply status filter if provided
    if status:
        try:
            status_enum = PipelineRunStatus(status)
            query = query.where(PipelineRun.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid status. Must be one of: running, completed, failed",
            )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Order by started_at DESC and paginate
    query = query.order_by(PipelineRun.started_at.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    runs = result.scalars().all()

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return AdminListResponse(
        items=[PipelineRunResponse.model_validate(run) for run in runs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/pipeline-runs/{run_id}", response_model=PipelineRunResponse)
@limiter.limit(RATE_LIMITS["admin"])
async def get_pipeline_run(
    request: Request,
    admin: AdminDep,
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PipelineRunResponse:
    """Get a single pipeline run by ID.

    Args:
        request: FastAPI request object for rate limiting
        admin: Authenticated admin user
        run_id: UUID of the pipeline run
        db: Database session

    Returns:
        Pipeline run details

    Raises:
        HTTPException: 404 if pipeline run not found
    """
    result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
    run = result.scalar_one_or_none()

    if run is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    return PipelineRunResponse.model_validate(run)


# ============================================================================
# Click Tracking Endpoints
# ============================================================================


@router.get("/clicks/by-user", response_model=list[ClicksByUserResponse])
@limiter.limit(RATE_LIMITS["admin"])
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
@limiter.limit(RATE_LIMITS["admin"])
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
@limiter.limit(RATE_LIMITS["admin"])
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
@limiter.limit(RATE_LIMITS["admin"])
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
@limiter.limit(RATE_LIMITS["admin"])
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
