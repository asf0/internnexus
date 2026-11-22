"""Ashby ATS adapter."""

from __future__ import annotations

import logging
from typing import Any, ClassVar, Literal

from pipeline.stages.ingest.sources.client_base import PipelineATSClient
from pipeline.stages.ingest.sources.utils import parse_iso_datetime, parse_job_type, parse_work_mode
from pipeline.domain import JobSchema

logger = logging.getLogger(__name__)

# Known Ashby company slugs (same as v1)
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


class AshbyClient(PipelineATSClient):
    """Enhanced Ashby client that extracts all available fields."""

    settings_attr: ClassVar[str] = "ashby_api_url"

    def _jobs_url(self, company_slug: str) -> str:
        return f"{self.base_url}/{company_slug}"

    def _request_params(self) -> dict[str, str]:
        return {"includeCompensation": "true"}

    def _extract_jobs(self, payload: Any) -> list[dict[str, Any]]:
        return payload.get("jobs", [])

    def _normalize_jobs(self, company_slug: str, jobs: list[dict[str, Any]]) -> list[JobSchema]:
        """Normalize Ashby jobs to JobSchema objects with all fields."""
        normalized: list[JobSchema] = []

        for job in jobs:
            normalized_job = self._normalize_job(company_slug, job)
            if normalized_job is not None:
                normalized.append(normalized_job)

        return normalized

    def _normalize_job(self, company_slug: str, job: dict[str, Any]) -> JobSchema | None:
        title = job.get("title", "").strip()
        if not title:
            return None
        locality, region, country, location = self._location_fields(job)
        return JobSchema(
            source="ashby",
            title=title,
            company=job.get("companyName") or company_slug.title(),
            location=location,
            city=locality or None,
            state=region or None,
            country=country or None,
            apply_url=job.get("applyUrl") or job.get("jobUrl", ""),
            description_text=job.get("descriptionPlain") or job.get("descriptionHtml", ""),
            posted_at=parse_iso_datetime(job.get("publishedAt")),
            job_type=parse_job_type(job.get("employmentType", "")),
            work_mode=self._determine_work_mode(job.get("isRemote"), location),
        )

    def _location_fields(self, job: dict[str, Any]) -> tuple[str, str, str, str]:
        address = self._extract_address(job)
        locality = address.get("locality", "")
        region = address.get("region", "")
        country = address.get("country", "")
        location = f"{locality}, {region}, {country}" if all((locality, region, country)) else job.get("location", "")
        return locality, region, country, location

    def _extract_address(self, job: dict[str, Any]) -> dict[str, str]:
        """Extract address components from Ashby address object.

        Returns:
            Dict with keys: region, country, locality (all optional)
        """
        address = job.get("address", {})
        if not isinstance(address, dict):
            return {}

        postal = address.get("postalAddress", {})
        if not isinstance(postal, dict):
            return {}

        return {
            "region": postal.get("addressRegion", ""),
            "country": postal.get("addressCountry", ""),
            "locality": postal.get("addressLocality", ""),
        }

    def _determine_work_mode(
        self, is_remote: bool | None, location: str
    ) -> Literal["remote", "hybrid", "on_site"] | None:
        """Determine work mode from isRemote flag and location string.

        Args:
            is_remote: Boolean from API (can be None)
            location: Location string

        Returns:
            WorkMode enum value or None
        """
        # If isRemote is explicitly True
        if is_remote is True:
            return "remote"

        # If isRemote is explicitly False
        if is_remote is False:
            return "on_site"

        # Fallback: parse from location text
        return parse_work_mode(location)
