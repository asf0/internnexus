from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class JobResponse(BaseModel):
    id: UUID
    title: str
    company: str
    location: str
    city: str | None = None
    state: str | None = None
    country: str | None = None
    apply_url: str
    description_text: str
    visa_sponsored: bool | None
    f1_friendly: bool | None
    job_category: str | None
    requires_sponsorship: bool | None
    requires_us_citizenship: bool | None
    application_closed: bool | None
    is_faang_plus: bool | None
    requires_advanced_degree: bool | None
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


class MatchResponse(BaseModel):
    matches: list[MatchResult]
    total: int
