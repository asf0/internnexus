"""SQLAlchemy implementation of JobRepository.

This is the pipeline-local SQLAlchemy projection over the shared database schema.
All other pipeline modules should use the repository protocol for database access.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, select, update

from pipeline.infra.job_cache import invalidate_job_detail_cache
from pipeline.infra.models import Job
from pipeline.repositories import JobLocationData, LocationUpdate
from pipeline.repositories.sync_ops import (
    SYNC_BATCH_SIZE,
    batched_delete_inactive,
)

__all__ = [
    "SQLAlchemyJobRepository",
]


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _location_scope_criteria(since: datetime | None, process_all: bool) -> list:
    """WHERE criteria for the cleanup job selection.

    since: active jobs seen since the timestamp; process_all: every active
    job with a location; default: only jobs never normalized.
    """
    if since:
        return [
            Job.is_active.is_(True),
            Job.last_seen >= since,
            Job.location.isnot(None),
        ]
    if process_all:
        return [
            Job.is_active.is_(True),
            Job.location.isnot(None),
        ]
    return [
        Job.is_active.is_(True),
        Job.location.isnot(None),
        Job.city.is_(None),
        Job.state.is_(None),
        Job.country.is_(None),
    ]


def _enum_str(value: Enum | str | None) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, str):
        return value
    return ""


class SQLAlchemyJobRepository:
    """SQLAlchemy implementation of job repository.

    This class implements the JobRepository protocol using SQLAlchemy 2.0
    async operations. It provides an abstraction layer over database access,
    allowing the rest of the pipeline to work with a clean interface while
    this class handles all the ORM-specific details.

    Usage:
        async with AsyncSessionLocal() as session:
            repo = SQLAlchemyJobRepository(session)
            jobs = await repo.fetch_jobs_batch_keyset(since=None, process_all=True, last_id=None, limit=100)
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self._session = session

    async def fetch_jobs_batch_keyset(
        self,
        since: datetime | None,
        process_all: bool,
        last_id: UUID | None,
        limit: int,
    ) -> list[JobLocationData]:
        """Fetch jobs with location data using keyset pagination."""
        stmt = select(
            Job.id,
            Job.source,
            Job.location,
            Job.city,
            Job.state,
            Job.country,
        )

        stmt = stmt.where(*_location_scope_criteria(since, process_all))

        if last_id is not None:
            stmt = stmt.where(Job.id > last_id)

        stmt = stmt.order_by(Job.id).limit(limit)
        result = await self._session.execute(stmt)
        rows = result.all()

        return [
            JobLocationData(
                id=row.id,
                source=_enum_str(row.source),
                location=row.location,
                city=row.city,
                state=row.state,
                country=row.country,
            )
            for row in rows
        ]

    async def update_job_locations(
        self,
        updates: list[LocationUpdate],
    ) -> int:
        """Batch update job locations using SQLAlchemy 2.0 bulk update.

        Uses bulk_update_mappings for optimal performance - reduces many individual
        UPDATE statements to a single bulk operation.

        Args:
            updates: List of location updates to apply

        Returns:
            Number of jobs updated
        """
        if not updates:
            return 0

        # Convert LocationUpdate objects to dicts for bulk update
        update_mappings = [
            {
                "id": update.job_id,
                "city": update.city,
                "state": update.state,
                "country": update.country,
            }
            for update in updates
        ]

        await self._session.execute(
            update(Job),
            update_mappings,
            execution_options={"synchronize_session": False},
        )
        await self._session.commit()
        await invalidate_job_detail_cache(update.job_id for update in updates)

        return len(updates)

    async def delete_inactive_jobs(
        self,
        sync_id: UUID,
        batch_size: int | None = None,
        max_attempts: int | None = None,
        base_delay: float | None = None,
        max_delay: float | None = None,
    ) -> int:
        """Delete inactive jobs that were not seen this run.

        Uses absence from the run-scoped sightings table.

        Args:
            sync_id: Synchronization run whose sightings define retained jobs.
            batch_size: Number of rows per batch. Defaults to SYNC_BATCH_SIZE.
            max_attempts: Maximum retry attempts. Defaults to 3.
            base_delay: Base delay in seconds. Defaults to 0.5.
            max_delay: Maximum delay in seconds. Defaults to 4.0.

        Returns:
            Number of jobs deleted
        """
        if batch_size is None:
            batch_size = SYNC_BATCH_SIZE
        return await batched_delete_inactive(
            self._session,
            sync_id,
            batch_size=batch_size,
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
        )

    async def get_total_count(
        self,
        since: datetime | None,
        process_all: bool,
    ) -> int:
        """Get total count of jobs to process.

        Args:
            since: Only count jobs updated since this timestamp
            process_all: If True, count all active jobs

        Returns:
            Total count of matching jobs
        """
        stmt = select(func.count()).select_from(Job)
        stmt = stmt.where(*_location_scope_criteria(since, process_all))

        result = await self._session.execute(stmt)
        return result.scalar() or 0
