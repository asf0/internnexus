"""Repository pattern for pipeline database operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TYPE_CHECKING, TypedDict
from uuid import UUID

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class JobLocationData:
    """Data class for job location info."""

    id: UUID
    source: str
    location: str | None
    city: str | None
    state: str | None
    country: str | None


@dataclass
class LocationUpdate:
    """Data class for location updates."""

    job_id: UUID
    city: str | None
    state: str | None
    country: str | None
    is_remote: bool


class JobEmbeddingRecord(TypedDict):
    """Projected job payload used by embedding/classification steps."""

    id: UUID
    company: str
    title: str
    apply_url: str
    description_text: str
    description_embedding: list[float] | None


class JobRepository(Protocol):
    """Protocol for job data access.

    This protocol defines the interface for job database operations,
    allowing for different implementations (SQLAlchemy, mock, etc.)
    while maintaining type safety.
    """

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
        ...

    async def fetch_jobs_batch_keyset(
        self,
        since: datetime | None,
        process_all: bool,
        last_id: UUID | None,
        limit: int,
    ) -> list[JobLocationData]:
        """Fetch jobs with location data using keyset pagination.

        Args:
            since: Only fetch jobs updated since this timestamp
            process_all: If True, fetch all active jobs regardless of since
            last_id: Last seen job UUID; fetch jobs strictly after this ID
            limit: Maximum number of records to fetch

        Returns:
            List of JobLocationData objects
        """
        ...

    async def update_job_locations(
        self,
        updates: list[LocationUpdate],
    ) -> int:
        """Batch update job locations.

        Args:
            updates: List of location updates to apply

        Returns:
            Number of jobs updated
        """
        ...

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
        ...

    async def get_jobs_by_ids(
        self,
        job_ids: list[UUID],
    ) -> list[JobEmbeddingRecord]:
        """Fetch jobs by their UUIDs.

        Args:
            job_ids: List of job UUIDs

        Returns:
            List of job data dictionaries
        """
        ...

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
        ...

    async def mark_all_jobs_inactive(self) -> int:
        """No-op in the last_seen sync model.

        Kept for backward compatibility.

        Returns:
            0
        """
        ...

    async def delete_inactive_jobs(self, batch_start_time: datetime) -> int:
        """Delete inactive jobs that were not seen this run.

        Args:
            batch_start_time: Jobs with ``last_seen`` older than this are
                eligible for deletion.

        Returns:
            Number of jobs deleted
        """
        ...

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
        ...


__all__ = [
    "JobLocationData",
    "LocationUpdate",
    "JobEmbeddingRecord",
    "JobRepository",
]
