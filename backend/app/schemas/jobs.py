"""Job listing request/response contracts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobSummaryResponse(BaseModel):
    id: UUID
    source: str
    title: str
    company: str
    location: str
    city: str | None = None
    state: str | None = None
    country: str | None = None
    apply_url: str
    job_category: str | None
    job_type: str | None
    work_mode: str | None
    posted_at: datetime | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class JobResponse(JobSummaryResponse):
    description_html: str
    description_truncated: bool = False


class JobListResponse(BaseModel):
    items: list[JobSummaryResponse]
    total: int
    page: int
    page_size: int


class SitemapJobResponse(BaseModel):
    """Minimal job projection for sitemap generation."""

    id: UUID
    posted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SitemapJobListResponse(BaseModel):
    """Sitemap id slice plus the total needed to size the chunk set."""

    items: list[SitemapJobResponse]
    total: int
