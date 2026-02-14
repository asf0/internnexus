from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from .utils import parse_iso_datetime
from ..schemas import JobSchema


class GreenhouseClient:
    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)
        self._settings = get_settings()
        self.base_url = self._settings.greenhouse_api_url

    def fetch_jobs(self, company_slug: str) -> list[JobSchema]:
        url = f"{self.base_url}/{company_slug}/jobs"
        response = self._client.get(url, params={"content": "true"})
        response.raise_for_status()
        payload = response.json()
        return self._normalize_jobs(company_slug, payload.get("jobs", []))

    def _normalize_jobs(self, company_slug: str, jobs: list[dict[str, Any]]) -> list[JobSchema]:
        normalized: list[JobSchema] = []
        for job in jobs:
            normalized.append(
                JobSchema(
                    source="greenhouse",
                    title=job.get("title", "").strip(),
                    company=job.get("company", {}).get("name") or company_slug,
                    location=(job.get("location", {}) or {}).get("name", "").strip(),
                    apply_url=job.get("absolute_url", ""),
                    description_text=job.get("content", "") or "",
                    posted_at=parse_iso_datetime(job.get("updated_at")),
                )
            )
        return normalized
