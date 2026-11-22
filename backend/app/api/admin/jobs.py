"""Admin job management routes."""

from __future__ import annotations

from typing import Annotated

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from internnexus_core.identity import fingerprint_for
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.admin import (
    AdminJobBulkRequest,
    AdminJobCreateRequest,
    AdminJobResponse,
    AdminJobUpdateRequest,
    AdminListResponse,
)
from app.schemas.mappers import job_to_admin_response
from app.auth.dependencies import AdminDep, SuperAdminDep
from app.infra.db import get_db
from app.models import Job, JobClick, JobSource, JobType, WorkMode
from app.infra.rate_limiter import RATE_LIMITS, limiter
from app.services.jobs.cache_invalidation import invalidate_job_detail_cache

from .shared import _add_admin_audit_log, paginate
from app.infra.commit import commit_or_500

router = APIRouter()
_JOB_NOT_FOUND = "Job not found"


async def _get_job_or_404(db: AsyncSession, job_id: UUID) -> Job:
    """Fetch a job by id or raise the admin 404."""
    job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail=_JOB_NOT_FOUND)
    return job


@router.get("/jobs")
@limiter.limit(RATE_LIMITS["admin_read"])
async def list_jobs(
    request: Request,
    admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1, description='Page number')] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description='Items per page')] = 20,
    search: Annotated[str | None, Query(description='Search in title and company')] = None,
    company: Annotated[str | None, Query(description='Filter by company name')] = None,
    category: Annotated[str | None, Query(description='Filter by job category')] = None,
    is_active: Annotated[bool | None, Query(description='Filter by active status')] = None,
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
    def _map(row) -> AdminJobResponse:
        return job_to_admin_response(row[0], click_count=int(row[1] or 0))

    return await paginate(
        db,
        base_query=query,
        page=page,
        page_size=page_size,
        mapper=_map,
        order_by=(Job.last_seen.desc(),),
    )


@router.get("/jobs/stats")
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_job_stats(
    request: Request,
    admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get job statistics for admin dashboard.

    Args:
        request: FastAPI request object for rate limiting
        admin: Authenticated admin user
        db: Database session

    Returns:
        Dictionary with job statistics including totals and breakdown by category
    """
    # Total, active, and distinct-company counts in one round-trip.
    totals_stmt = select(
        func.count(Job.id).label("total_jobs"),
        func.count(Job.id).filter(Job.is_active.is_(True)).label("active_jobs"),
        func.count(func.distinct(Job.company)).label("total_companies"),
    ).select_from(Job)
    totals = (await db.execute(totals_stmt)).one()

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
        "total_jobs": totals.total_jobs,
        "active_jobs": totals.active_jobs,
        "total_companies": totals.total_companies,
        "jobs_by_category": jobs_by_category,
    }


@router.get("/jobs/{job_id}", responses={404: {"description": "Not found"}})
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_job(
    request: Request,
    job_id: UUID,
    admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
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
        raise HTTPException(status_code=404, detail=_JOB_NOT_FOUND)

    job = row[0]
    click_count = row[1]

    return job_to_admin_response(job, click_count=int(click_count or 0))


@router.patch("/jobs/{job_id}", responses={404: {"description": "Not found"}})
@limiter.limit(RATE_LIMITS["admin_write"])
async def update_job(
    request: Request,
    job_id: UUID,
    update_data: AdminJobUpdateRequest,
    admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
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
    job = await _get_job_or_404(db, job_id)

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
    await commit_or_500(db, operation="update job", detail="Database operation failed")
    await invalidate_job_detail_cache([job_id])
    await db.refresh(job)

    # Get click count
    click_result = await db.execute(select(func.count(JobClick.id)).where(JobClick.job_id == job_id))
    click_count = click_result.scalar() or 0

    return job_to_admin_response(job, click_count=int(click_count or 0))


@router.delete("/jobs/{job_id}", responses={404: {"description": "Not found"}})
@limiter.limit(RATE_LIMITS["admin_write"])
async def delete_job(
    request: Request,
    job_id: UUID,
    admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
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
    job = await _get_job_or_404(db, job_id)

    # Soft delete
    job.is_active = False
    await _add_admin_audit_log(
        db,
        actor_user_id=admin.user_id,
        action="job.deactivate",
        target_type="job",
        target_id=job_id,
    )
    await commit_or_500(db, operation="deactivate job", detail="Database operation failed")
    await invalidate_job_detail_cache([job_id])

    return {"message": "Job deactivated"}


@router.post("/jobs", status_code=201, responses={400: {"description": "Bad request"}})
@limiter.limit(RATE_LIMITS["admin_write"])
async def create_job(
    request: Request,
    data: AdminJobCreateRequest,
    admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
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
    # Generate fingerprint using shared scheme (same as pipeline)
    fingerprint = fingerprint_for(data.apply_url)

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
    await commit_or_500(db, operation="create job", detail="Database operation failed")
    await invalidate_job_detail_cache([new_job.id])
    await db.refresh(new_job)

    return job_to_admin_response(new_job, click_count=0)


@router.delete("/jobs/{job_id}/hard", responses={400: {"description": "Bad request"}, 404: {"description": "Not found"}})
@limiter.limit(RATE_LIMITS["admin_destructive"])
async def hard_delete_job(
    request: Request,
    job_id: UUID,
    super_admin: SuperAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
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
    job = await _get_job_or_404(db, job_id)

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
    await commit_or_500(db, operation="hard delete job", detail="Database operation failed")
    await invalidate_job_detail_cache([job_id])

    return {"message": "Job permanently deleted"}


@router.post("/jobs/bulk", responses={400: {"description": "Bad request"}})
@limiter.limit(RATE_LIMITS["admin_bulk"])
async def bulk_job_action(
    request: Request,
    data: AdminJobBulkRequest,
    super_admin: SuperAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
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
    await commit_or_500(db, operation="bulk job action", detail="Database operation failed")
    await invalidate_job_detail_cache([job.id for job in jobs])

    return {"affected_count": len(jobs), "action": data.action}
