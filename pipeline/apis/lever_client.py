"""Enhanced Lever client that extracts all available fields from the Lever API.

This is v2 of the Lever client which extracts all fields discovered from API analysis.
It's designed to be compatible with an extended JobSchema that you'll add DB columns for later.

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

    # NEW FIELDS to add:
    external_id: str | None = None
    commitment: str | None = None  # "Full Time", "Contract", etc.
    department: str | None = None
    team: str | None = None
    all_locations: list[str] | None = None
    workplace_type: str | None = None  # direct from API

    # Salary
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_interval: str | None = None
    salary_description: str | None = None
    salary_description_plain: str | None = None

    # Content variants
    opening_html: str | None = None
    opening_plain: str | None = None
    description_html: str | None = None  # full HTML
    description_plain: str | None = None  # full plain text
    description_body_html: str | None = None  # role only
    description_body_plain: str | None = None
    additional_html: str | None = None
    additional_plain: str | None = None

    # Requirements
    requirements: list[dict] | None = None  # structured
    requirements_html: str | None = None
    requirements_plain: str | None = None
    has_requirements: bool | None = None
    requirements_count: int | None = None

    hosted_url: str | None = None
    created_at: int | None = None  # raw timestamp
```
"""

from __future__ import annotations

from typing import Any

import httpx

from pipeline.backend_bridge import get_settings
from pipeline.apis.utils import parse_unix_timestamp, parse_job_type, parse_work_mode
from pipeline.schemas import JobSchema


def parse_requirements(lists: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Parse the lists/requirements section from Lever.

    Returns:
        dict with:
        - requirements: list of dicts with title, content_html, content_plain
        - requirements_html: concatenated HTML content
        - requirements_plain: concatenated plain text
    """
    if not lists:
        return {
            "requirements": [],
            "requirements_html": "",
            "requirements_plain": "",
        }

    requirements = []
    html_parts = []
    plain_parts = []

    for item in lists:
        title = item.get("text", "")
        content_html = item.get("content", "")
        # Note: Lever doesn't provide plain text for lists content
        # We're storing HTML only - if you need plain text later,
        # you'll need to strip HTML tags

        requirements.append(
            {
                "title": title,
                "content_html": content_html,
                "content_plain": "",  # No plain version available from API
            }
        )

        if title:
            html_parts.append(f"<h3>{title}</h3>")
            plain_parts.append(f"{title}:")

        html_parts.append(content_html)
        plain_parts.append("")  # No plain version

    return {
        "requirements": requirements,
        "requirements_html": "\n".join(html_parts),
        "requirements_plain": "\n\n".join(plain_parts),
    }


class LeverClient:
    """Enhanced Lever client that extracts all available fields."""

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)
        self._settings = get_settings()
        self.base_url = self._settings.lever_api_url

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> LeverClient:
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        self.close()

    def fetch_jobs(self, company_slug: str) -> list[JobSchema]:
        """Fetch all jobs for a company and return complete field extraction.

        Args:
            company_slug: The Lever company identifier (e.g., "bounteous", "stripe")

        Returns:
            List of JobSchema objects with all fields from Lever API
        """
        url = f"{self.base_url}/{company_slug}"
        response = self._client.get(url, params={"mode": "json"})
        response.raise_for_status()
        payload = response.json()
        return self._normalize_jobs(company_slug, payload)

    def _normalize_jobs(self, company_slug: str, jobs: list[dict[str, Any]]) -> list[JobSchema]:
        """Normalize Lever jobs to JobSchema objects with all fields."""
        normalized: list[JobSchema] = []

        for job in jobs:
            categories = job.get("categories", {}) or {}
            salary = job.get("salaryRange") or {}
            location_str = categories.get("location", "").strip()

            # Parse requirements
            req_data = parse_requirements(job.get("lists"))

            # Build JobSchema with all fields
            job_schema = JobSchema(
                # Core identification
                source="lever",
                title=job.get("text", "").strip(),
                company=company_slug,
                location=location_str,
                country=job.get("country"),
                apply_url=job.get("applyUrl", ""),
                description_text=job.get("description", ""),
                posted_at=parse_unix_timestamp(job.get("createdAt")),
                job_type=parse_job_type(categories.get("commitment", "")),
                work_mode=parse_work_mode(job.get("workplaceType", "")),
                # NEW FIELDS (add these to JobSchema later):
                external_id=job.get("id"),
                commitment=categories.get("commitment"),
                department=categories.get("department"),
                team=categories.get("team"),
                all_locations=categories.get("allLocations", []),
                workplace_type=job.get("workplaceType"),
                salary_min=salary.get("min"),
                salary_max=salary.get("max"),
                salary_currency=salary.get("currency"),
                salary_interval=salary.get("interval"),
                salary_description=job.get("salaryDescription", ""),
                salary_description_plain=job.get("salaryDescriptionPlain", ""),
                opening_html=job.get("opening", ""),
                opening_plain=job.get("openingPlain", ""),
                description_html=job.get("description", ""),
                description_plain=job.get("descriptionPlain", ""),
                description_body_html=job.get("descriptionBody", ""),
                description_body_plain=job.get("descriptionBodyPlain", ""),
                additional_html=job.get("additional", ""),
                additional_plain=job.get("additionalPlain", ""),
                requirements=req_data["requirements"],
                requirements_html=req_data["requirements_html"],
                requirements_plain=req_data["requirements_plain"],
                has_requirements=bool(job.get("lists")),
                requirements_count=len(job.get("lists", [])),
                hosted_url=job.get("hostedUrl", ""),
                created_at=job.get("createdAt"),
            )

            normalized.append(job_schema)

        return normalized
