from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from ..schemas import JobSchema


class GreenhouseClient:
    base_url = "https://boards-api.greenhouse.io/v1/boards"

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

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
                    posted_at=self._parse_datetime(job.get("updated_at")),
                )
            )
        return normalized

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
