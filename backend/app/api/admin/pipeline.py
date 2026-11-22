"""Admin pipeline run and command routes."""

from __future__ import annotations

from typing import Annotated

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.admin import (
    AdminListResponse,
    PipelineCommandResponse,
    PipelineCommandTriggerRequest,
    PipelineRunResponse,
)
from app.auth.dependencies import AdminDep
from app.infra.db import get_db
from app.models import PipelineCommand, PipelineCommandStatus, PipelineRun, PipelineRunStatus
from app.infra.rate_limiter import RATE_LIMITS, limiter

from .shared import VALID_PIPELINE_STEPS, _add_admin_audit_log, paginate
from app.infra.commit import commit_or_500

router = APIRouter()

# ============================================================================
# Pipeline Run Endpoints
# ============================================================================


@router.get("/pipeline-runs/stats")
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_pipeline_stats(
    request: Request,
    admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get pipeline run statistics.

    Args:
        request: FastAPI request object for rate limiting
        admin: Authenticated admin user
        db: Database session

    Returns:
        Dictionary with pipeline statistics
    """
    # Per-status counts in one round-trip.
    counts_stmt = select(
        func.count(PipelineRun.id).label("total_runs"),
        func.count(PipelineRun.id)
        .filter(PipelineRun.status == PipelineRunStatus.completed)
        .label("completed"),
        func.count(PipelineRun.id)
        .filter(PipelineRun.status == PipelineRunStatus.failed)
        .label("failed"),
        func.count(PipelineRun.id)
        .filter(PipelineRun.status == PipelineRunStatus.running)
        .label("running"),
    ).select_from(PipelineRun)
    counts = (await db.execute(counts_stmt)).one()

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
        "total_runs": counts.total_runs,
        "completed": counts.completed,
        "failed": counts.failed,
        "running": counts.running,
        "last_success": last_success,
        "last_failure": last_failure,
    }


@router.get("/pipeline-runs/latest")
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_latest_pipeline_run(
    request: Request,
    admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
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


@router.get("/pipeline-runs", responses={400: {"description": "Bad request"}})
@limiter.limit(RATE_LIMITS["admin_read"])
async def list_pipeline_runs(
    request: Request,
    admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1, description='Page number')] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description='Items per page')] = 20,
    status: Annotated[str | None, Query(description='Filter by status (running, completed, failed)')] = None,
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
    return await paginate(
        db,
        base_query=query,
        page=page,
        page_size=page_size,
        mapper=PipelineRunResponse.model_validate,
        order_by=(PipelineRun.started_at.desc(),),
        scalars=True,
    )




@router.post("/pipeline-runs/trigger", status_code=202, responses={400: {"description": "Bad request"}})
@limiter.limit(RATE_LIMITS["admin_write"])
async def trigger_pipeline_run(
    request: Request,
    data: PipelineCommandTriggerRequest,
    admin: AdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
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
    await commit_or_500(db, operation="trigger pipeline run", detail="Database operation failed")
    await db.refresh(command)
    return PipelineCommandResponse.model_validate(command)


@router.get("/pipeline-runs/{run_id}", responses={404: {"description": "Not found"}})
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_pipeline_run(
    request: Request,
    admin: AdminDep,
    run_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
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
