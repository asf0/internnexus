"""Location cleanup module - normalize city/state/country fields."""

from __future__ import annotations

import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.models import Job
from ingestion.data.constants import US_STATES, US_STATE_NAMES, STATE_NAMES_TO_ABBR

logger = logging.getLogger(__name__)

COUNTRY_ALIASES = {
    "usa": "United States",
    "us": "United States",
    "u.s.": "United States",
    "united states": "United States",
    "united states of america": "United States",
    "uk": "United Kingdom",
    "gb": "United Kingdom",
    "great britain": "United Kingdom",
    "ca": "Canada",
    "canada": "Canada",
    "au": "Australia",
    "australia": "Australia",
    "de": "Germany",
    "germany": "Germany",
    "fr": "France",
    "france": "France",
    "remote": "Remote",
}


def clean_location(location: str) -> dict:
    """Parse and normalize a location string."""
    if not location:
        return {"location": "", "city": None, "state": None, "country": None}

    original = location.strip()
    parts = [p.strip() for p in re.split(r"[,/]", original) if p.strip()]

    city, state, country = None, None, None

    for part in parts:
        part_lower = part.lower()

        # Check country
        if part_lower in COUNTRY_ALIASES:
            country = COUNTRY_ALIASES[part_lower]
            continue

        # Check US state abbreviation
        if part.upper() in US_STATES:
            state = part.upper()
            country = country or "United States"
            continue

        # Check US state full name
        if part_lower in US_STATE_NAMES:
            state = STATE_NAMES_TO_ABBR[part_lower]
            country = country or "United States"
            continue

        # Otherwise treat as city
        if not city and len(part) > 1:
            city = part.title()

    # Build normalized location
    loc_parts = []
    if city:
        loc_parts.append(city)
    if state:
        loc_parts.append(state)
    if country:
        loc_parts.append(country)

    normalized = ", ".join(loc_parts) if loc_parts else original

    return {"location": normalized, "city": city, "state": state, "country": country}


async def cleanup_locations(session: AsyncSession | None = None) -> int:
    """Normalize location data for all jobs."""
    logger.info("=" * 60)
    logger.info("STEP 3: Cleaning up locations...")
    logger.info("=" * 60)

    should_close_session = session is None
    if should_close_session:
        session = AsyncSessionLocal()

    try:
        result = await session.execute(select(Job).where(Job.is_active == True))
        jobs = result.scalars().all()
        logger.info(f"Found {len(jobs)} active jobs to process")

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
                job.location = result["location"]
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
