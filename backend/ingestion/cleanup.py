"""Location cleanup module - normalize city/state/country fields."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.models import Job
from ingestion.location_normalizer import clean_location

logger = logging.getLogger(__name__)


async def cleanup_locations(
    session: AsyncSession | None = None, since: datetime | None = None, process_all: bool = False
) -> int:
    """Normalize location data for jobs.

    Args:
        session: Database session. If None, creates a new session.
        since: Only process jobs updated since this timestamp. If None, processes all active jobs.
        process_all: If True, re-process all active jobs with locations. If False and no since,
                     only processes jobs that haven't been normalized yet.

    Returns:
        Number of jobs updated
    """
    logger.info("=" * 60)
    logger.info("STEP 3: Cleaning up locations...")
    logger.info("=" * 60)

    should_close_session = session is None
    if should_close_session:
        session = AsyncSessionLocal()

    try:
        if since:
            result = await session.execute(
                select(Job).where(Job.is_active == True, Job.last_seen >= since)
            )
            logger.info(f"Processing jobs updated since {since.isoformat()}")
        elif process_all:
            result = await session.execute(
                select(Job).where(Job.is_active == True, Job.location.isnot(None))
            )
            logger.info("Processing ALL active jobs with locations")
        else:
            result = await session.execute(
                select(Job).where(
                    Job.is_active == True,
                    Job.location.isnot(None),
                    Job.city.is_(None),
                    Job.state.is_(None),
                    Job.country.is_(None),
                )
            )
            logger.info("Processing jobs that have not been normalized yet")

        jobs = result.scalars().all()
        logger.info(f"Found {len(jobs)} jobs to process")

        updated = 0
        for job in jobs:
            if not job.location:
                continue

            result = clean_location(job.location)

            changed = (
                result["location"] != job.location
                or result["city"] != job.city
                or result["state"] != job.state
                or result["country"] != job.country
            )

            if changed:
                if result["location"] is not None:
                    job.location = result["location"]
                else:
                    logger.debug(
                        f"Location normalization returned None for job {job.id}, preserving original: {job.location}"
                    )
                job.city = result["city"]
                job.state = result["state"]
                job.country = result["country"]
                updated += 1

        await session.commit()
        logger.info(f"Updated {updated} job locations")
        return updated
    finally:
        if should_close_session:
            await session.close()


async def delete_old_jobs(session: AsyncSession | None = None, days: int = 7) -> int:
    """
    Permanently delete jobs that haven't been seen in X days.

    Args:
        session: Database session (creates new one if None)
        days: Delete jobs older than this many days (default: 7)

    Returns:
        Number of jobs deleted
    """
    logger.info("=" * 60)
    logger.info(f"STEP: Deleting jobs older than {days} days...")
    logger.info("=" * 60)

    should_close_session = session is None
    if should_close_session:
        session = AsyncSessionLocal()

    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Count before deletion
        result = await session.execute(
            select(func.count()).select_from(Job).where(Job.last_seen < cutoff_date)
        )
        count_to_delete = result.scalar()

        if count_to_delete == 0:
            logger.info("No old jobs to delete")
            return 0

        logger.info(f"Deleting {count_to_delete} jobs older than {days} days")

        # Delete old jobs permanently
        result = await session.execute(delete(Job).where(Job.last_seen < cutoff_date))
        await session.commit()

        deleted_count = result.rowcount
        logger.info(f"Successfully deleted {deleted_count} old jobs")
        return deleted_count

    finally:
        if should_close_session:
            await session.close()
