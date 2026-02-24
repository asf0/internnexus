from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class JobResponse(BaseModel):
    id: UUID
    source: str
    title: str
    company: str
    location: str
    city: str | None = None
    state: str | None = None
    country: str | None = None
    apply_url: str
    description_text: str
    job_category: str | None
    job_type: str | None
    work_mode: str | None
    posted_at: datetime | None
    is_active: bool

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int


class MatchResult(BaseModel):
    job_id: UUID
    score: float
    match_percentage: float = Field(..., ge=0, le=100)
    title: str
    company: str
    location: str
    apply_url: str
    description_text: str
    city: str | None = None
    state: str | None = None
    country: str | None = None
    job_category: str | None = None
    job_type: str | None = None
    work_mode: str | None = None
    posted_at: datetime | None = None
    score_breakdown: dict[str, float] | None = None


class MatchResponse(BaseModel):
    matches: list[MatchResult]
    total: int
    session_id: str
    page: int = 1
    page_size: int
    total_pages: int
    reused_from_cache: bool = False


class JobMatchResult(BaseModel):
    """Job with match score for paginated match results."""

    job: JobResponse
    score: float
    match_percentage: float = Field(..., ge=0, le=100)


class PaginatedMatchResponse(BaseModel):
    """Response for paginated match results with full job details."""

    items: list[JobMatchResult]
    total: int
    session_id: str
    page: int
    page_size: int
    total_pages: int
