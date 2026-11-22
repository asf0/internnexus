"""Greenhouse ATS adapter."""

from __future__ import annotations

import re
from typing import Any, ClassVar

from pipeline.stages.ingest.sources.client_base import PipelineATSClient
from pipeline.stages.ingest.sources.utils import (
    parse_iso_datetime,
    detect_job_type_from_title,
    detect_work_mode_from_text,
)
from pipeline.domain import JobSchema


class GreenhouseClient(PipelineATSClient):
    """Enhanced Greenhouse client that extracts all available fields."""

    settings_attr: ClassVar[str] = "greenhouse_api_url"

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

    def _jobs_url(self, company_slug: str) -> str:
        return f"{self.base_url}/{company_slug}/jobs"

    def _request_params(self) -> dict[str, str]:
        return {"content": "true"}

    def _extract_jobs(self, payload: Any) -> list[dict[str, Any]]:
        return payload.get("jobs", [])

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
        if not content or not content.strip():
            return True
        text = re.sub(r"<[^>]+>", "", content)
        text = re.sub(r"&[a-z]+;", "", text)
        text = text.strip()
        return len(text) < 10

    def _normalize_jobs(self, company_slug: str, jobs: list[dict[str, Any]]) -> list[JobSchema]:
        """Normalize Greenhouse jobs to JobSchema objects with all fields."""
        normalized: list[JobSchema] = []

        for job in jobs:
            # Extract location (raw, no parsing)
            location_obj = job.get("location", {}) or {}
            location = (location_obj.get("name") or "").strip()

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
            )

            normalized.append(job_schema)

        return normalized
