from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from .utils import parse_unix_timestamp, parse_job_type, parse_work_mode
from ..schemas import JobSchema


class LeverClient:
    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)
        self._settings = get_settings()
        self.base_url = self._settings.lever_api_url

    def fetch_jobs(self, company_slug: str) -> list[JobSchema]:
        url = f"{self.base_url}/{company_slug}"
        response = self._client.get(url, params={"mode": "json"})
        response.raise_for_status()
        payload = response.json()
        return self._normalize_jobs(company_slug, payload)

    def _normalize_jobs(self, company_slug: str, jobs: list[dict[str, Any]]) -> list[JobSchema]:
        normalized: list[JobSchema] = []
        for job in jobs:
            title = job.get("text", "").strip()
            location = (job.get("categories", {}) or {}).get("location", "").strip()
            commitment = (job.get("categories", {}) or {}).get("commitment", "")
            workplace_type = (job.get("categories", {}) or {}).get("workplaceType", "")
            job_type = parse_job_type(commitment)
            work_mode = parse_work_mode(workplace_type)
            normalized.append(
                JobSchema(
                    source="lever",
                    title=title,
                    company=company_slug,
                    location=location,
                    apply_url=job.get("hostedUrl", ""),
                    description_text=job.get("description", "") or "",
                    posted_at=parse_unix_timestamp(job.get("createdAt")),
                    job_type=job_type,
                    work_mode=work_mode,
                )
            )
        return normalized
