"""SQLAlchemy implementation of JobRepository.

This is the pipeline-local SQLAlchemy projection over the shared database schema.
All other pipeline modules should use the repository protocol for database access.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, select, text, update

from pipeline.db import AsyncSessionLocal
from pipeline.models import (
    Job,
    JobSource,
    PipelineRun,
    PipelineRunStatus,
)
from pipeline.repositories import JobEmbeddingRecord, JobLocationData, LocationUpdate
from pipeline.repositories.job_text_sql import embedding_candidate_text_sql
from pipeline.repositories.sync_ops import (
    batched_delete_inactive,
)

__all__ = [
    "AsyncSessionLocal",
    "Job",
    "JobSource",
    "PipelineRun",
    "PipelineRunStatus",
    "SQLAlchemyJobRepository",
    "get_repository",
]


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _enum_str(value: Enum | str | None) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, str):
        return value
    return ""


def _rowcount(result: object) -> int:
    raw_rowcount = getattr(result, "rowcount", None)
    if isinstance(raw_rowcount, int):
        return raw_rowcount
    return int(raw_rowcount or 0)


class SQLAlchemyJobRepository:
    """SQLAlchemy implementation of job repository.

    This class implements the JobRepository protocol using SQLAlchemy 2.0
    async operations. It provides an abstraction layer over database access,
    allowing the rest of the pipeline to work with a clean interface while
    this class handles all the ORM-specific details.

    Usage:
        async with AsyncSessionLocal() as session:
            repo = SQLAlchemyJobRepository(session)
            jobs = await repo.fetch_jobs_batch(since=None, process_all=True, offset=0, limit=100)
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self._session = session

    async def fetch_jobs_batch(
        self,
        since: datetime | None,
        process_all: bool,
        offset: int,
        limit: int,
    ) -> list[JobLocationData]:
        """Fetch jobs with location data.

        Args:
            since: Only fetch jobs updated since this timestamp
            process_all: If True, fetch all active jobs regardless of since
            offset: Number of records to skip
            limit: Maximum number of records to fetch

        Returns:
            List of JobLocationData objects
        """
        # Build base query with required columns
        stmt = select(
            Job.id,
            Job.source,
            Job.location,
            Job.city,
            Job.state,
            Job.country,
        )

        # Apply filters
        if since:
            stmt = stmt.where(
                Job.is_active.is_(True),
                Job.last_seen >= since,
                Job.location.isnot(None),
            )
        elif process_all:
            stmt = stmt.where(
                Job.is_active.is_(True),
                Job.location.isnot(None),
            )
        else:
            # Default: only jobs that haven't been normalized yet
            stmt = stmt.where(
                Job.is_active.is_(True),
                Job.location.isnot(None),
                Job.city.is_(None),
                Job.state.is_(None),
                Job.country.is_(None),
            )

        # Apply pagination
        stmt = stmt.offset(offset).limit(limit)

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

        if since:
            stmt = stmt.where(
                Job.is_active.is_(True),
                Job.last_seen >= since,
                Job.location.isnot(None),
            )
        elif process_all:
            stmt = stmt.where(
                Job.is_active.is_(True),
                Job.location.isnot(None),
            )
        else:
            stmt = stmt.where(
                Job.is_active.is_(True),
                Job.location.isnot(None),
                Job.city.is_(None),
                Job.state.is_(None),
                Job.country.is_(None),
            )

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

        return len(updates)

    async def refresh_search_vectors_for_job_ids(self, job_ids: list[UUID]) -> int:
        """Recompute search vectors for given job IDs.

        Args:
            job_ids: List of job UUIDs to refresh

        Returns:
            Number of rows updated
        """
        if not job_ids:
            return 0

        search_vector_expr = text(
            """
            setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(company, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(location, '')), 'C') ||
            setweight(to_tsvector('english', COALESCE(city, '')), 'C') ||
            setweight(to_tsvector('english', COALESCE(state, '')), 'C') ||
            setweight(to_tsvector('english', get_country_search_terms(country)), 'C') ||
            setweight(to_tsvector('english', get_region_from_country(country)), 'C') ||
            setweight(to_tsvector('english', COALESCE(description_text, '')), 'D')
            """
        )
        refresh_stmt = update(Job).where(Job.id.in_(job_ids)).values(search_vector=search_vector_expr)
        result = await self._session.execute(refresh_stmt)
        await self._session.commit()
        return _rowcount(result)

    async def get_jobs_without_embeddings(
        self,
        batch_size: int,
    ) -> list[UUID]:
        """Get job IDs that need embeddings generated.

        Filters out jobs with empty/short description text (< 30 chars
        after stripping HTML) since they cannot be meaningfully embedded.

        Args:
            batch_size: Maximum number of job IDs to fetch

        Returns:
            List of job IDs (UUID primary keys)
        """
        cleaned_text = embedding_candidate_text_sql()

        stmt = (
            select(Job.id)
            .where(Job.description_embedding.is_(None))
            .where(Job.embedding_skip_reason.is_(None))
            .where(func.length(cleaned_text) >= 30)
            .order_by(Job.id)
            .limit(batch_size)
        )

        result = await self._session.execute(stmt)
        job_ids = result.scalars().all()
        return list(job_ids)

    async def get_jobs_by_ids(
        self,
        job_ids: list[UUID],
    ) -> list[JobEmbeddingRecord]:
        """Fetch jobs by their integer IDs.

        Args:
            job_ids: List of job UUIDs

        Returns:
            List of job data dictionaries with id, company, title, apply_url
        """
        if not job_ids:
            return []

        stmt = select(
            Job.id,
            Job.company,
            Job.title,
            Job.apply_url,
            Job.description_text,
            Job.description_embedding,
        ).where(Job.id.in_(job_ids))

        result = await self._session.execute(stmt)
        rows = result.all()

        return [
            {
                "id": row.id,
                "company": row.company,
                "title": row.title,
                "apply_url": row.apply_url,
                "description_text": row.description_text,
                "description_embedding": row.description_embedding,
            }
            for row in rows
        ]

    async def update_job_embedding(
        self,
        job_id: UUID,
        embedding: list[float],
    ) -> None:
        """Update a job's embedding vector.

        Args:
            job_id: The job's UUID
            embedding: The embedding vector to store
        """
        stmt = update(Job).where(Job.id == job_id).values(
            description_embedding=embedding,
            embedding_skip_reason=None,
            embedding_skipped_at=None,
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def mark_all_jobs_inactive(self) -> int:
        """No-op in the last_seen sync model.

        Kept for backward compatibility. The actual stale-job marking is done
        after ingestion via ``batched_mark_stale_jobs_inactive``.

        Returns:
            0
        """
        return 0

    async def delete_inactive_jobs(self, batch_start_time: datetime) -> int:
        """Delete inactive jobs that were not seen this run.

        Uses ``last_seen < batch_start_time`` to ensure only jobs from prior
        runs are deleted, providing a safety buffer against partial ingests.

        Args:
            batch_start_time: Timestamp captured at the start of ingestion.

        Returns:
            Number of jobs deleted
        """
        return await batched_delete_inactive(self._session, batch_start_time)

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

        if since:
            stmt = stmt.where(
                Job.is_active.is_(True),
                Job.last_seen >= since,
                Job.location.isnot(None),
            )
        elif process_all:
            stmt = stmt.where(
                Job.is_active.is_(True),
                Job.location.isnot(None),
            )
        else:
            stmt = stmt.where(
                Job.is_active.is_(True),
                Job.location.isnot(None),
                Job.city.is_(None),
                Job.state.is_(None),
                Job.country.is_(None),
            )

        result = await self._session.execute(stmt)
        return result.scalar() or 0


# Factory function for convenient repository creation
async def get_repository() -> SQLAlchemyJobRepository:
    """Get a repository instance with a fresh session.

    This is a convenience function for getting a repository
    without manually creating a session.

    Usage:
        async with get_repository() as repo:
            jobs = await repo.fetch_jobs_batch(...)
    """
    session = AsyncSessionLocal()
    return SQLAlchemyJobRepository(session)
