"""Admin pipeline run and command routes."""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_schemas import (
    AdminListResponse,
    PipelineCommandResponse,
    PipelineCommandTriggerRequest,
    PipelineRunResponse,
)
from app.auth.dependencies import AdminDep
from app.db import get_db
from app.models import PipelineCommand, PipelineCommandStatus, PipelineRun, PipelineRunStatus
from app.rate_limiter import RATE_LIMITS, limiter

from .shared import VALID_PIPELINE_STEPS, _add_admin_audit_log, _commit_or_500

router = APIRouter()

# ============================================================================
# Pipeline Run Endpoints
# ============================================================================


@router.get("/pipeline-runs/stats")
@limiter.limit(RATE_LIMITS["admin_read"])
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
@limiter.limit(RATE_LIMITS["admin_read"])
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
@limiter.limit(RATE_LIMITS["admin_read"])
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




@router.post("/pipeline-runs/trigger", response_model=PipelineCommandResponse, status_code=202)
@limiter.limit(RATE_LIMITS["admin_write"])
async def trigger_pipeline_run(
    request: Request,
    data: PipelineCommandTriggerRequest,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
) -> PipelineCommandResponse:
    """Enqueue a pipeline command for the pipeline process to claim.

    The backend records intent only; it does not import or execute pipeline code.
    """
    if data.step is not None and data.step not in VALID_PIPELINE_STEPS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid step. Must be one of: {sorted(VALID_PIPELINE_STEPS)}",
        )

    command = PipelineCommand(
        status=PipelineCommandStatus.pending,
        step=data.step,
        skip_discover=data.skip_discover,
        dry_run=data.dry_run,
        process_all=data.process_all,
        test_mode=data.test_mode,
        limit=data.limit,
        requested_by=admin.user_id,
    )
    db.add(command)
    await db.flush()
    await _add_admin_audit_log(
        db,
        actor_user_id=admin.user_id,
        action="pipeline_command.create",
        target_type="pipeline_command",
        target_id=command.id,
        metadata={"step": command.step, "dry_run": command.dry_run, "limit": command.limit},
    )
    await _commit_or_500(db, "trigger pipeline run")
    await db.refresh(command)
    return PipelineCommandResponse.model_validate(command)


@router.get("/pipeline-runs/{run_id}", response_model=PipelineRunResponse)
@limiter.limit(RATE_LIMITS["admin_read"])
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
