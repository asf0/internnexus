"""Enhanced Greenhouse client that extracts all available fields from the Greenhouse API.

This is v2 of the Greenhouse client which extracts all fields discovered from API analysis.
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

    # NEW FIELDS from Greenhouse:
    external_id: str | None = None          # id (numeric in GH, convert to string)
    internal_job_id: int | None = None      # internal_job_id
    requisition_id: str | None = None       # requisition_id
    education: str | None = None            # education (education_required/optional)
    language: str | None = None             # language (en, ja, etc.)
    first_published: datetime | None = None # first_published
    updated_at: datetime | None = None      # updated_at (different from posted_at)

    # Arrays (stored as JSONB or separate tables later)
    departments: list[dict] | None = None   # departments array with id, name, child_ids, parent_id
    offices: list[dict] | None = None       # offices array with id, name, location, child_ids, parent_id
    data_compliance: list[dict] | None = None # GDPR compliance data

    # Metadata
    metadata: dict | None = None            # custom metadata (often null)

    # URLs
    hosted_url: str | None = None           # absolute_url
```
"""

from __future__ import annotations

from typing import Any

import httpx

from pipeline.backend_bridge import get_settings
from pipeline.apis.utils import (
    parse_iso_datetime,
    detect_job_type_from_title,
    detect_work_mode_from_text,
)
from pipeline.schemas import JobSchema


class GreenhouseClient:
    """Enhanced Greenhouse client that extracts all available fields."""

    METADATA_DESCRIPTION_FIELDS = [
        "In short",
        "Your mission",
        "Your story",
        "Meet the team",
        "What we offer",
        "About the role",
        "About the team",
        "Responsibilities",
        "Requirements",
        "Qualifications",
        "Benefits",
        "The role",
    ]

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)
        self._settings = get_settings()
        self.base_url = self._settings.greenhouse_api_url

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> GreenhouseClient:
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        self.close()

    def _extract_description_from_metadata(self, metadata: list[dict] | None) -> str:
        """Build description text from metadata array when content field is empty.

        Some companies (e.g., On Running) store job descriptions in structured metadata
        instead of the content field. This extracts and combines relevant fields.
        """
        if not metadata:
            return ""

        sections = []
        for field in self.METADATA_DESCRIPTION_FIELDS:
            for item in metadata:
                if item.get("name") == field and item.get("value"):
                    value = item["value"]
                    sections.append(f"## {field}\n\n{value}")
                    break

        return "\n\n".join(sections)

    def _is_content_empty(self, content: str) -> bool:
        """Check if content is effectively empty (no real text after stripping HTML)."""
        import re

        if not content or not content.strip():
            return True
        text = re.sub(r"<[^>]+>", "", content)
        text = re.sub(r"&[a-z]+;", "", text)
        text = text.strip()
        return len(text) < 10

    def fetch_jobs(self, company_slug: str) -> list[JobSchema]:
        """Fetch all jobs for a company and return complete field extraction.

        Args:
            company_slug: The Greenhouse company identifier (e.g., "stripe", "appliedintuition")

        Returns:
            List of JobSchema objects with all fields from Greenhouse API
        """
        url = f"{self.base_url}/{company_slug}/jobs"
        response = self._client.get(url, params={"content": "true"})
        response.raise_for_status()
        payload = response.json()
        return self._normalize_jobs(company_slug, payload.get("jobs", []))

    def _normalize_jobs(self, company_slug: str, jobs: list[dict[str, Any]]) -> list[JobSchema]:
        """Normalize Greenhouse jobs to JobSchema objects with all fields."""
        normalized: list[JobSchema] = []

        for job in jobs:
            # Extract location (raw, no parsing)
            location_obj = job.get("location", {}) or {}
            location = location_obj.get("name", "").strip()

            # Extract company name
            company_name = job.get("company_name") or company_slug

            # Detect job type and work mode from title/location (for backward compatibility)
            title = job.get("title", "").strip()
            job_type = detect_job_type_from_title(title)
            work_mode = detect_work_mode_from_text(title, location)

            content = job.get("content", "") or ""
            metadata = job.get("metadata")
            if self._is_content_empty(content) and metadata:
                content = self._extract_description_from_metadata(metadata)

            job_schema = JobSchema(
                source="greenhouse",
                title=title,
                company=company_name,
                location=location,
                apply_url=job.get("absolute_url", ""),
                description_text=content,
                posted_at=parse_iso_datetime(job.get("first_published")),
                job_type=job_type,
                work_mode=work_mode,
                # NEW FIELDS (add these to JobSchema later):
                external_id=str(job.get("id")) if job.get("id") else None,
                internal_job_id=job.get("internal_job_id"),
                requisition_id=job.get("requisition_id"),
                education=job.get("education"),
                language=job.get("language"),
                first_published=parse_iso_datetime(job.get("first_published")),
                updated_at=parse_iso_datetime(job.get("updated_at")),
                departments=job.get("departments", []),
                offices=job.get("offices", []),
                data_compliance=job.get("data_compliance", []),
                metadata=job.get("metadata"),
                hosted_url=job.get("absolute_url", ""),
            )

            normalized.append(job_schema)

        return normalized
