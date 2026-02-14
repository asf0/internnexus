"""Workday API client for fetching job postings.

Workday is used by many large enterprises (Stripe, Airbnb, Netflix, Salesforce, etc.)
API format: https://myworkdayjobs.com/{tenant}/jobs or internal API endpoints
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .utils import parse_iso_datetime
from ..schemas import JobSchema

logger = logging.getLogger(__name__)

WORKDAY_KNOWN_TENANTS = [
    "stripe",
    "airbnb",
    "netflix",
    "salesforce",
    "adobe",
    "nvidia",
    "cisco",
    "oracle",
    "vmware",
    "atlassian",
    "dropbox",
    "lyft",
    "instacart",
    "splunk",
    "workday",
]


class WorkdayClient:
    WORKDAY_API_BASE = "https://myworkdayjobs.com/wday/cxs"

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

    def fetch_jobs(self, tenant: str, sub_path: str = "") -> list[JobSchema]:
        url = (
            f"{self.WORKDAY_API_BASE}/{tenant}/{sub_path}jobs"
            if sub_path
            else f"{self.WORKDAY_API_BASE}/{tenant}/jobs"
        )
        jobs: list[JobSchema] = []
        try:
            response = self._client.get(url)
            response.raise_for_status()
            payload = response.json()
            return self._normalize_jobs(tenant, payload.get("jobPostings", []))
        except Exception as exc:
            logger.warning("Workday fetch failed for %s: %s", tenant, exc)
            return jobs

    def fetch_all_tenants(self, tenants: list[str] | None = None) -> list[JobSchema]:
        jobs: list[JobSchema] = []
        tenants = tenants or WORKDAY_KNOWN_TENANTS
        for tenant in tenants:
            try:
                jobs.extend(self.fetch_jobs(tenant))
            except Exception as exc:
                logger.debug("Workday tenant %s failed: %s", tenant, exc)
        return jobs

    def _normalize_jobs(self, tenant: str, jobs: list[dict[str, Any]]) -> list[JobSchema]:
        normalized: list[JobSchema] = []
        for job in jobs:
            title = job.get("title", "").strip()
            if not title:
                continue
            location = self._extract_location(job)
            description = job.get("jobPostingInfo", {}).get("jobDescription", "") or ""
            if not description:
                description = job.get("description", "") or ""
            apply_url = (
                job.get("externalUrl")
                or f"https://myworkdayjobs.com/{tenant}/job/{job.get('jobPostingId', '')}"
            )
            normalized.append(
                JobSchema(
                    source="workday",
                    title=title,
                    company=job.get("companyName") or tenant.title(),
                    location=location,
                    apply_url=apply_url,
                    description_text=description,
                    posted_at=parse_iso_datetime(job.get("postedOn")),
                )
            )
        return normalized

    def _extract_location(self, job: dict[str, Any]) -> str:
        locations = job.get("locations", [])
        if locations and isinstance(locations, list):
            loc_parts = []
            for loc in locations[:1]:
                if isinstance(loc, dict):
                    city = loc.get("city", "")
                    state = loc.get("state", "")
                    country = loc.get("country", "")
                    if city:
                        loc_parts.append(city)
                    if state:
                        loc_parts.append(state)
                    if country:
                        loc_parts.append(country)
                elif isinstance(loc, str):
                    loc_parts.append(loc)
            return ", ".join(loc_parts) if loc_parts else "Remote"
        return job.get("location", "Remote") or "Remote"
