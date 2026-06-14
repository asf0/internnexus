"""Enhanced Ashby client that extracts all available fields from the Ashby API.

This is v2 of the Ashby client which extracts all fields discovered from API analysis.
It's designed to be compatible with an extended JobSchema that you'll add DB columns for later.

Ashby is used by fast-growing startups (Notion, Linear, Vercel, Ramp, Mercury, etc.)
API: https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true

Extended JobSchema to add to schemas.py later:
```python
class JobSchema(BaseModel):
    # Existing fields
    source: JobSource
    title: str
    company: str
    location: str
    city: str | None = None
    state: str | None = None
    country: str | None = None
    apply_url: str
    description_text: str
    posted_at: datetime | None = None
    visa_sponsored: bool | None = None
    f1_friendly: bool | None = None
    job_category: JobCategory | None = None
    job_type: JobType | None = None
    work_mode: WorkMode | None = None
    requires_sponsorship: bool | None = None
    requires_us_citizenship: bool | None = None
    application_closed: bool | None = None
    is_faang_plus: bool | None = None
    requires_advanced_degree: bool | None = None
    description_embedding: list[float] | None = None

    # NEW FIELDS from Ashby:

    # Core identifiers
    external_id: str | None = None              # id (UUID string)
    company_name: str | None = None             # companyName (from API)

    # Job details
    department: str | None = None               # department (string) or department.name
    team: str | None = None                     # team (separate from department)
    employment_type: str | None = None          # employmentType: FullTime, Contract, Intern, Temporary

    # Locations
    location_raw: str | None = None             # location (raw string like "San Francisco, California")
    secondary_locations: list[str] | None = None # secondaryLocations (array of strings)
    is_remote: bool | None = None               # isRemote (nullable boolean)

    # Address (parsed from address.postalAddress)
    address_region: str | None = None           # addressRegion (e.g., "California")
    address_country: str | None = None          # addressCountry (e.g., "United States")
    address_locality: str | None = None         # addressLocality (e.g., "San Francisco")
    address_raw: dict | None = None             # Raw address object

    # URLs
    job_url: str | None = None                  # jobUrl
    apply_url: str | None = None                # applyUrl

    # Content variants
    description_html: str | None = None         # descriptionHtml (full HTML)
    description_plain: str | None = None        # descriptionPlain (full plain text)

    # Status & visibility
    is_listed: bool | None = None               # isListed
    should_display_compensation: bool | None = None  # shouldDisplayCompensationOnJobPostings

    # Compensation (full object - usually empty in API responses)
    compensation: dict | None = None            # compensation object with:
                                                #   - compensationTierSummary
                                                #   - scrapeableCompensationSalarySummary
                                                #   - compensationTiers[]
                                                #   - summaryComponents[]

    # Timestamps
    updated_at: datetime | None = None          # updatedAt (different from posted_at/publishedAt)
```

Example Ashby API response structure:
{
    "id": "34664867-7190-479c-8a8c-2a9612b532ea",
    "title": "Senior Stock Plan Administrator",
    "department": "Legal",  # or {"name": "Legal"} in some cases
    "team": "Legal",
    "employmentType": "FullTime",
    "location": "San Francisco, California",
    "shouldDisplayCompensationOnJobPostings": false,
    "secondaryLocations": [],
    "publishedAt": "2026-02-05T22:23:45.355+00:00",
    "updatedAt": "2026-02-05T22:23:45.355+00:00",
    "isListed": true,
    "isRemote": null,
    "address": {
        "postalAddress": {
            "addressRegion": "California",
            "addressCountry": "United States",
            "addressLocality": "San Francisco"
        }
    },
    "jobUrl": "https://jobs.ashbyhq.com/notion/34664867-7190-479c-8a8c-2a9612b532ea",
    "applyUrl": "https://jobs.ashbyhq.com/notion/34664867-7190-479c-8a8c-2a9612b532ea/application",
    "descriptionHtml": "<h1>About Us:</h1><p>...</p>",
    "descriptionPlain": "ABOUT US:\n\nNotion helps you...",
    "compensation": {
        "compensationTierSummary": null,
        "scrapeableCompensationSalarySummary": null,
        "compensationTiers": [],
        "summaryComponents": []
    }
}
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from pipeline.config import get_settings
from pipeline.sources.utils import parse_iso_datetime, parse_job_type, parse_work_mode
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


class AshbyClient:
    """Enhanced Ashby client that extracts all available fields."""

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)
        self._settings = get_settings()
        self.base_url = "https://api.ashbyhq.com/posting-api/job-board"

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> AshbyClient:
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        self.close()

    def fetch_jobs(self, company_slug: str) -> list[JobSchema]:
        """Fetch all jobs for a company and return complete field extraction.

        Args:
            company_slug: The Ashby company identifier (e.g., "notion", "linear", "vercel")

        Returns:
            List of JobSchema objects with all fields from Ashby API
        """
        url = f"{self.base_url}/{company_slug}"
        response = self._client.get(url, params={"includeCompensation": "true"})
        response.raise_for_status()
        payload = response.json()
        return self._normalize_jobs(company_slug, payload.get("jobs", []))

    def fetch_all_slugs(self, slugs: list[str] | None = None) -> list[JobSchema]:
        """Fetch jobs from all known Ashby slugs.

        Args:
            slugs: Optional list of slugs to fetch. Uses ASHBY_KNOWN_SLUGS if not provided.

        Returns:
            List of JobSchema objects from all companies
        """
        jobs: list[JobSchema] = []
        slugs = slugs or ASHBY_KNOWN_SLUGS
        for slug in slugs:
            try:
                jobs.extend(self.fetch_jobs(slug))
            except Exception as exc:  # noqa: BLE001  # one failed slug should not stop the rest
                logger.debug("Ashby v2 slug %s failed: %s", slug, exc)
        return jobs

    def _normalize_jobs(self, company_slug: str, jobs: list[dict[str, Any]]) -> list[JobSchema]:
        """Normalize Ashby jobs to JobSchema objects with all fields."""
        normalized: list[JobSchema] = []

        for job in jobs:
            title = job.get("title", "").strip()
            if not title:
                continue

            # Extract department (can be string or dict with name)
            department = job.get("department", "")
            if isinstance(department, dict):
                department = department.get("name", "")

            # Extract address components first
            address_data = self._extract_address(job)
            locality = address_data.get("locality", "")
            region = address_data.get("region", "")
            country = address_data.get("country", "")

            # Build location from address fields if available, otherwise use raw location
            if locality and region and country:
                location_str = f"{locality}, {region}, {country}"
            else:
                location_str = job.get("location", "")

            # Parse job type and work mode from employment type
            employment_type = job.get("employmentType", "")
            job_type = parse_job_type(employment_type)

            # Determine work mode from isRemote and location
            is_remote = job.get("isRemote")
            work_mode = self._determine_work_mode(is_remote, location_str)

            # Build JobSchema with ALL fields
            job_schema = JobSchema(
                # Core fields (existing)
                source="ashby",
                title=title,
                company=job.get("companyName") or company_slug.title(),
                location=location_str,
                city=locality if locality else None,
                state=region if region else None,
                country=country if country else None,
                apply_url=job.get("applyUrl") or job.get("jobUrl", ""),
                description_text=job.get("descriptionPlain") or job.get("descriptionHtml", ""),
                posted_at=parse_iso_datetime(job.get("publishedAt")),
                job_type=job_type,
                work_mode=work_mode,
                # NEW FIELDS (add these to JobSchema later):
                external_id=job.get("id"),
                company_name=job.get("companyName"),
                department=department,
                team=job.get("team", ""),
                employment_type=employment_type,
                location_raw=location_str,
                secondary_locations=job.get("secondaryLocations", []),
                is_remote=is_remote,
                address_region=address_data.get("region"),
                address_country=address_data.get("country"),
                address_locality=address_data.get("locality"),
                address_raw=job.get("address"),
                job_url=job.get("jobUrl", ""),
                description_html=job.get("descriptionHtml", ""),
                description_plain=job.get("descriptionPlain", ""),
                is_listed=job.get("isListed"),
                should_display_compensation=job.get("shouldDisplayCompensationOnJobPostings"),
                compensation=job.get("compensation", {}),
                updated_at=parse_iso_datetime(job.get("updatedAt")),
            )

            normalized.append(job_schema)

        return normalized

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

    def _determine_work_mode(self, is_remote: bool | None, location: str) -> str | None:
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
