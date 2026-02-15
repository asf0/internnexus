"""SmartRecruiters API client for fetching job postings.

SmartRecruiters is used by mid-size to large companies.
API: https://api.smartrecruiters.com/v1/companies/{slug}/postings
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .utils import parse_iso_datetime, parse_job_type, parse_work_mode
from ..schemas import JobSchema

logger = logging.getLogger(__name__)

SMARTRECRUITERS_KNOWN_SLUGS = [
    "GitLab",
    "McAfee",
    "Bosch",
    "Biogen",
    "Nvidia",
    "Veeam",
    "Arista",
    "PureStorage",
    "Guidewire",
    "Anaplan",
]


class SmartRecruitersClient:
    SMARTRECRUITERS_API_BASE = "https://api.smartrecruiters.com/v1/companies"

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

    def fetch_jobs(self, slug: str) -> list[JobSchema]:
        url = f"{self.SMARTRECRUITERS_API_BASE}/{slug}/postings"
        jobs: list[JobSchema] = []
        try:
            response = self._client.get(url, params={"limit": 100})
            response.raise_for_status()
            payload = response.json()
            return self._normalize_jobs(slug, payload.get("content", []))
        except Exception as exc:
            logger.warning("SmartRecruiters fetch failed for %s: %s", slug, exc)
            return jobs

    def fetch_all_slugs(self, slugs: list[str] | None = None) -> list[JobSchema]:
        jobs: list[JobSchema] = []
        slugs = slugs or SMARTRECRUITERS_KNOWN_SLUGS
        for slug in slugs:
            try:
                jobs.extend(self.fetch_jobs(slug))
            except Exception as exc:
                logger.debug("SmartRecruiters slug %s failed: %s", slug, exc)
        return jobs

    def _normalize_jobs(self, slug: str, jobs: list[dict[str, Any]]) -> list[JobSchema]:
        normalized: list[JobSchema] = []
        for job in jobs:
            title = job.get("name", "").strip()
            if not title:
                continue
            location = self._extract_location(job)
            description = job.get("jobAd", {}).get("sections", [])
            description_text = self._extract_description(description)
            apply_url = job.get("applyUrl", "")
            if not apply_url:
                job_id = job.get("id", "")
                apply_url = f"https://jobs.smartrecruiters.com/{slug}/{job_id}"
            employment_type = (
                job.get("typeOfEmployment", {}).get("label", "")
                if isinstance(job.get("typeOfEmployment"), dict)
                else job.get("typeOfEmployment", "")
            )
            workplace_type = job.get("workplaceType", "")
            job_type = parse_job_type(employment_type)
            work_mode = parse_work_mode(workplace_type)
            normalized.append(
                JobSchema(
                    source="smartrecruiters",
                    title=title,
                    company=job.get("company", {}).get("name") or slug,
                    location=location,
                    apply_url=apply_url,
                    description_text=description_text,
                    posted_at=parse_iso_datetime(job.get("releasedDate")),
                    job_type=job_type,
                    work_mode=work_mode,
                )
            )
        return normalized

    def _extract_location(self, job: dict[str, Any]) -> str:
        location = job.get("location", {})
        if isinstance(location, dict):
            city = location.get("city", "")
            region = location.get("region", "")
            country = location.get("country", "")
            parts = [p for p in [city, region, country] if p]
            if parts:
                return ", ".join(parts)
        if isinstance(location, str):
            return location
        return "Remote"

    def _extract_description(self, sections: list[dict[str, Any]]) -> str:
        if not sections:
            return ""
        text_parts = []
        for section in sections:
            if isinstance(section, dict):
                title = section.get("title", "")
                content = section.get("text", "")
                if title:
                    text_parts.append(f"## {title}")
                if content:
                    text_parts.append(content)
        return "\n\n".join(text_parts)
