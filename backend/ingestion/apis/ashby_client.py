"""Ashby API client for fetching job postings.

Ashby is used by fast-growing startups (Notion, Linear, Vercel, Ramp, Mercury, etc.)
API: https://api.ashbyhq.com/posting-api/{slug}
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .utils import parse_iso_datetime, parse_job_type, parse_work_mode
from ..schemas import JobSchema

logger = logging.getLogger(__name__)

ASHBY_KNOWN_SLUGS = [
    "notion",
    "linear",
    "vercel",
    "ramp",
    "mercury",
    "luminary",
    "guna",
    "descript",
    "rook",
    "lattice",
    "fauna",
    "planetscale",
    "pitch",
    "vital",
    "string",
]


class AshbyClient:
    ASHBY_API_BASE = "https://api.ashbyhq.com/posting-api"

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

    def fetch_jobs(self, slug: str) -> list[JobSchema]:
        url = f"{self.ASHBY_API_BASE}/{slug}"
        jobs: list[JobSchema] = []
        try:
            response = self._client.get(url)
            response.raise_for_status()
            payload = response.json()
            return self._normalize_jobs(slug, payload.get("jobs", []))
        except Exception as exc:
            logger.warning("Ashby fetch failed for %s: %s", slug, exc)
            return jobs

    def fetch_all_slugs(self, slugs: list[str] | None = None) -> list[JobSchema]:
        jobs: list[JobSchema] = []
        slugs = slugs or ASHBY_KNOWN_SLUGS
        for slug in slugs:
            try:
                jobs.extend(self.fetch_jobs(slug))
            except Exception as exc:
                logger.debug("Ashby slug %s failed: %s", slug, exc)
        return jobs

    def _normalize_jobs(self, slug: str, jobs: list[dict[str, Any]]) -> list[JobSchema]:
        normalized: list[JobSchema] = []
        for job in jobs:
            title = job.get("title", "").strip()
            if not title:
                continue
            location = self._extract_location(job)
            description = job.get("descriptionHtml", "") or job.get("description", "") or ""
            apply_url = job.get("jobUrl") or job.get("applicationUrl", "")
            if not apply_url:
                apply_url = f"https://jobs.ashbyhq.com/{slug}/{job.get('id', '')}"
            employment_type = job.get("employmentType", "")
            location_type = job.get("locationType", "")
            job_type = parse_job_type(employment_type)
            work_mode = parse_work_mode(location_type)
            normalized.append(
                JobSchema(
                    source="ashby",
                    title=title,
                    company=job.get("companyName") or slug.title(),
                    location=location,
                    apply_url=apply_url,
                    description_text=description,
                    posted_at=parse_iso_datetime(job.get("publishedAt")),
                    job_type=job_type,
                    work_mode=work_mode,
                )
            )
        return normalized

    def _extract_location(self, job: dict[str, Any]) -> str:
        location = job.get("location", {})
        if isinstance(location, dict):
            parts = []
            city = location.get("city")
            state = location.get("state")
            country = location.get("country")
            if city:
                parts.append(city)
            if state:
                parts.append(state)
            if country:
                parts.append(country)
            if parts:
                return ", ".join(parts)
        if isinstance(location, str):
            return location
        locations = job.get("locations", [])
        if locations and isinstance(locations, list):
            return locations[0] if locations[0] else "Remote"
        return "Remote"
