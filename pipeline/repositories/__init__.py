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


class JobRepository(Protocol):
    """Protocol for job data access.

    This protocol defines the interface for job database operations,
    allowing for different implementations (SQLAlchemy, mock, etc.)
    while maintaining type safety.
    """

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

    async def delete_inactive_jobs(self, sync_id: UUID) -> int:
        """Delete inactive jobs that were not seen this run.

        Args:
            sync_id: Synchronization run whose sightings define retained jobs.

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
    "JobRepository",
]
