"""Admin job management routes."""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_schemas import (
    AdminJobBulkRequest,
    AdminJobCreateRequest,
    AdminJobResponse,
    AdminJobUpdateRequest,
    AdminListResponse,
)
from app.api.mappers import job_to_admin_response
from app.auth.dependencies import AdminDep, SuperAdminDep
from app.db import get_db
from app.models import Job, JobClick, JobSource, JobType, WorkMode
from app.rate_limiter import RATE_LIMITS, limiter

from .shared import _add_admin_audit_log, _commit_or_500

router = APIRouter()


@router.get("/jobs", response_model=AdminListResponse[AdminJobResponse])
@limiter.limit(RATE_LIMITS["admin_read"])
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
        select(JobClick.job_id, func.count(JobClick.id).label("click_count")).group_by(JobClick.job_id).subquery()
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
            (func.lower(Job.title).ilike(search_pattern)) | (func.lower(Job.company).ilike(search_pattern))
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
        click_count = int(row[1] or 0)
        items.append(job_to_admin_response(job, click_count=click_count))

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return AdminListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/jobs/stats")
@limiter.limit(RATE_LIMITS["admin_read"])
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
    active_result = await db.execute(select(func.count()).select_from(Job).where(Job.is_active.is_(True)))
    active_jobs = active_result.scalar() or 0

    # Total companies (distinct)
    companies_result = await db.execute(select(func.count(func.distinct(Job.company))).select_from(Job))
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
@limiter.limit(RATE_LIMITS["admin_read"])
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

    return job_to_admin_response(job, click_count=int(click_count or 0))


@router.patch("/jobs/{job_id}", response_model=AdminJobResponse)
@limiter.limit(RATE_LIMITS["admin_write"])
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

    await _add_admin_audit_log(
        db,
        actor_user_id=admin.user_id,
        action="job.update",
        target_type="job",
        target_id=job_id,
        metadata={"fields": sorted(update_fields)},
    )
    await _commit_or_500(db, "update job")
    await db.refresh(job)

    # Get click count
    click_result = await db.execute(select(func.count(JobClick.id)).where(JobClick.job_id == job_id))
    click_count = click_result.scalar() or 0

    return job_to_admin_response(job, click_count=int(click_count or 0))


@router.delete("/jobs/{job_id}")
@limiter.limit(RATE_LIMITS["admin_write"])
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
    await _add_admin_audit_log(
        db,
        actor_user_id=admin.user_id,
        action="job.deactivate",
        target_type="job",
        target_id=job_id,
    )
    await _commit_or_500(db, "deactivate job")

    return {"message": "Job deactivated"}


@router.post("/jobs", response_model=AdminJobResponse, status_code=201)
@limiter.limit(RATE_LIMITS["admin_write"])
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
    fingerprint = hashlib.sha256(f"{data.title}{data.company}{data.apply_url}".encode()).hexdigest()[:64]

    # Check for duplicate fingerprint
    existing_result = await db.execute(select(Job).where(Job.fingerprint == fingerprint))
    existing_job = existing_result.scalar_one_or_none()

    if existing_job:
        raise HTTPException(status_code=400, detail="Job with this title, company, and URL already exists")

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
    await db.flush()
    await _add_admin_audit_log(
        db,
        actor_user_id=admin.user_id,
        action="job.create",
        target_type="job",
        target_id=new_job.id,
        metadata={"source": JobSource.manual.value},
    )
    await _commit_or_500(db, "create job")
    await db.refresh(new_job)

    return job_to_admin_response(new_job, click_count=0)


@router.delete("/jobs/{job_id}/hard")
@limiter.limit(RATE_LIMITS["admin_destructive"])
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
    await _add_admin_audit_log(
        db,
        actor_user_id=super_admin.user_id,
        action="job.hard_delete",
        target_type="job",
        target_id=job_id,
        metadata={"title": job.title, "company": job.company},
    )
    await db.delete(job)
    await _commit_or_500(db, "hard delete job")

    return {"message": "Job permanently deleted"}


@router.post("/jobs/bulk")
@limiter.limit(RATE_LIMITS["admin_bulk"])
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

    await _add_admin_audit_log(
        db,
        actor_user_id=super_admin.user_id,
        action=f"job.bulk_{data.action}",
        target_type="job",
        metadata={"job_ids": [str(job_id) for job_id in data.job_ids], "affected_count": len(jobs)},
    )
    await _commit_or_500(db, "bulk job action")

    return {"affected_count": len(jobs), "action": data.action}
