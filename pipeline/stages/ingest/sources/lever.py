"""Lever ATS adapter."""

from __future__ import annotations

from typing import Any, ClassVar

from pipeline.stages.ingest.sources.client_base import PipelineATSClient
from pipeline.stages.ingest.sources.utils import parse_unix_timestamp, parse_job_type, parse_work_mode
from pipeline.domain import JobSchema


class LeverClient(PipelineATSClient):
    """Enhanced Lever client that extracts all available fields."""

    settings_attr: ClassVar[str] = "lever_api_url"

    def _jobs_url(self, company_slug: str) -> str:
        return f"{self.base_url}/{company_slug}"

    def _request_params(self) -> dict[str, str]:
        return {"mode": "json"}

    def _extract_jobs(self, payload: Any) -> list[dict[str, Any]]:
        return payload

    def _normalize_jobs(self, company_slug: str, jobs: list[dict[str, Any]]) -> list[JobSchema]:
        """Normalize Lever jobs to JobSchema objects with all fields."""
        normalized: list[JobSchema] = []

        for job in jobs:
            categories = job.get("categories", {}) or {}
            location_str = categories.get("location", "").strip()

            # Build JobSchema with all fields
            job_schema = JobSchema(
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
            )

            normalized.append(job_schema)

        return normalized
