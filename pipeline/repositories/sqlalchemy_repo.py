"""SQLAlchemy implementation of JobRepository.

This is the ONLY file in the pipeline module that imports from backend.app.models.
All other pipeline modules should use the repository protocol for database access.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import delete, func, select, text, update

from backend.app.db import AsyncSessionLocal
from backend.app.models import (
    AshbyJobMetadata,
    GreenhouseJobMetadata,
    Job,
    JobSource,
    LeverJobMetadata,
    PipelineRun,
    PipelineRunStatus,
)
from pipeline.repositories import JobEmbeddingRecord, JobLocationData, LocationUpdate, MetadataBatch

__all__ = [
    "AsyncSessionLocal",
    "Job",
    "JobSource",
    "PipelineRun",
    "PipelineRunStatus",
    "AshbyJobMetadata",
    "GreenhouseJobMetadata",
    "LeverJobMetadata",
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

        job_id_strs = [f"('{str(uuid)}')" for uuid in job_ids]
        values_clause = ", ".join(job_id_strs)
        refresh_stmt = text(
            f"""
            UPDATE jobs AS j
            SET search_vector =
                setweight(to_tsvector('english', COALESCE(j.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(j.company, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(j.location, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(j.city, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(j.state, '')), 'C') ||
                setweight(to_tsvector('english', get_country_search_terms(j.country)), 'C') ||
                setweight(to_tsvector('english', get_region_from_country(j.country)), 'C') ||
                setweight(to_tsvector('english', COALESCE(j.description_text, '')), 'D')
            FROM (VALUES {values_clause}) AS t(job_id)
            WHERE j.id = t.job_id::uuid
            """
        )
        result = await self._session.execute(refresh_stmt)
        await self._session.commit()
        return _rowcount(result)

    async def fetch_metadata_batch(
        self,
        job_ids: list[UUID],
    ) -> MetadataBatch:
        """Fetch metadata for a batch of jobs using JOIN query.

        This method uses a single JOIN query to fetch all metadata at once,
        eliminating the N+1 query problem that would occur with separate
        queries for each metadata type.

        Args:
            job_ids: List of job IDs to fetch metadata for

        Returns:
            MetadataBatch containing metadata from all sources
        """
        if not job_ids:
            return MetadataBatch(ashby={}, greenhouse={}, lever={})

        # Single JOIN query to fetch all metadata at once
        # This is much more efficient than 4 separate queries
        stmt = (
            select(
                Job.id,
                AshbyJobMetadata.address_locality,
                AshbyJobMetadata.address_region,
                AshbyJobMetadata.address_country,
                GreenhouseJobMetadata.offices,
                LeverJobMetadata.all_locations,
            )
            .outerjoin(AshbyJobMetadata, AshbyJobMetadata.job_id == Job.id)
            .outerjoin(GreenhouseJobMetadata, GreenhouseJobMetadata.job_id == Job.id)
            .outerjoin(LeverJobMetadata, LeverJobMetadata.job_id == Job.id)
            .where(Job.id.in_(job_ids))
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        # Organize results by source
        ashby_map: dict[UUID, dict] = {}
        greenhouse_map: dict[UUID, dict] = {}
        lever_map: dict[UUID, dict] = {}

        for row in rows:
            job_id = row.id

            # Ashby metadata
            if row.address_locality:
                ashby_map[job_id] = {
                    "address_locality": row.address_locality,
                    "address_region": row.address_region,
                    "address_country": row.address_country,
                }

            # Greenhouse metadata
            if row.offices:
                greenhouse_map[job_id] = {"offices": row.offices}

            # Lever metadata
            if row.all_locations:
                lever_map[job_id] = {"all_locations": row.all_locations}

        return MetadataBatch(
            ashby=ashby_map,
            greenhouse=greenhouse_map,
            lever=lever_map,
        )

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
        # Clean HTML and entities from description_text
        cleaned_text = func.regexp_replace(
            func.regexp_replace(
                func.regexp_replace(Job.description_text, r"<[^\u003e]+>", " ", "g"),
                r"&[a-zA-Z]+;",
                " ",
                "g",
            ),
            r"\s+",
            " ",
            "g",
        )

        stmt = (
            select(Job.id)
            .where(Job.description_embedding.is_(None))
            .where(func.length(func.trim(cleaned_text)) >= 30)
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
        stmt = update(Job).where(Job.id == job_id).values(description_embedding=embedding)
        await self._session.execute(stmt)
        await self._session.commit()

    async def mark_all_jobs_inactive(self) -> int:
        """Mark all active jobs as inactive.

        This is part of the sync model: before fetching from APIs,
        we mark all jobs as inactive. Jobs that still exist in the
        API will be re-activated during upsert.

        Returns:
            Number of jobs marked inactive
        """
        stmt = update(Job).where(Job.is_active.is_(True)).values(is_active=False)
        result = await self._session.execute(stmt)
        await self._session.commit()
        return _rowcount(result)

    async def delete_inactive_jobs(self) -> int:
        """Delete all jobs marked as inactive.

        After marking all jobs inactive and re-ingesting from APIs,
        any jobs that remain inactive were not found in the APIs
        and should be deleted.

        Returns:
            Number of jobs deleted
        """
        stmt = delete(Job).where(Job.is_active.is_(False))
        result = await self._session.execute(stmt)
        await self._session.commit()
        return _rowcount(result)

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
