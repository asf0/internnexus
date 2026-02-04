from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from ..schemas import JobSchema


class LeverClient:
    base_url = "https://api.lever.co/v0/postings"

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

    def fetch_jobs(self, company_slug: str) -> list[JobSchema]:
        url = f"{self.base_url}/{company_slug}"
        response = self._client.get(url, params={"mode": "json"})
        response.raise_for_status()
        payload = response.json()
        return self._normalize_jobs(company_slug, payload)

    def _normalize_jobs(self, company_slug: str, jobs: list[dict[str, Any]]) -> list[JobSchema]:
        normalized: list[JobSchema] = []
        for job in jobs:
            normalized.append(
                JobSchema(
                    source="lever",
                    title=job.get("text", "").strip(),
                    company=company_slug,
                    location=(job.get("categories", {}) or {}).get("location", "").strip(),
                    apply_url=job.get("hostedUrl", ""),
                    description_text=job.get("description", "") or "",
                    posted_at=self._parse_datetime(job.get("createdAt")),
                )
            )
        return normalized

    @staticmethod
    def _parse_datetime(value: int | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.utcfromtimestamp(value / 1000)
        except (TypeError, ValueError, OSError):
            return None
