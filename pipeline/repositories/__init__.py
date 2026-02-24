"""Repository pattern for pipeline database operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TYPE_CHECKING
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


@dataclass
class MetadataBatch:
    """Data class for batch metadata results."""

    ashby: dict[UUID, dict]
    greenhouse: dict[UUID, dict]
    lever: dict[UUID, dict]


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

    async def fetch_metadata_batch(
        self,
        job_ids: list[UUID],
    ) -> MetadataBatch:
        """Fetch metadata for a batch of jobs.

        Uses JOIN query to fetch all metadata in a single query
        instead of N+1 separate queries.

        Args:
            job_ids: List of job IDs to fetch metadata for

        Returns:
            MetadataBatch containing metadata from all sources
        """
        ...

    async def get_jobs_without_embeddings(
        self,
        batch_size: int,
    ) -> list[int]:
        """Get job IDs that need embeddings generated.

        Filters out jobs with empty/short description text (< 30 chars
        after stripping HTML) since they cannot be meaningfully embedded.

        Args:
            batch_size: Maximum number of job IDs to fetch

        Returns:
            List of job IDs (integer primary keys)
        """
        ...

    async def get_jobs_by_ids(
        self,
        job_ids: list[int],
    ) -> list[dict]:
        """Fetch jobs by their integer IDs.

        Args:
            job_ids: List of job integer IDs

        Returns:
            List of job data dictionaries
        """
        ...

    async def update_job_embedding(
        self,
        job_id: int,
        embedding: list[float],
    ) -> None:
        """Update a job's embedding vector.

        Args:
            job_id: The job's integer ID
            embedding: The embedding vector to store
        """
        ...

    async def mark_all_jobs_inactive(self) -> int:
        """Mark all active jobs as inactive.

        This is part of the sync model: before fetching from APIs,
        we mark all jobs as inactive. Jobs that still exist in the
        API will be re-activated during upsert.

        Returns:
            Number of jobs marked inactive
        """
        ...

    async def delete_inactive_jobs(self) -> int:
        """Delete all jobs marked as inactive.

        After marking all jobs inactive and re-ingesting from APIs,
        any jobs that remain inactive were not found in the APIs
        and should be deleted.

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
    "MetadataBatch",
    "JobRepository",
]
