"""Resume-matching request/response contracts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MatchSummaryResponse(BaseModel):
    job_id: UUID
    score: float
    match_percentage: float = Field(..., ge=0, le=100)
    title: str
    company: str
    location: str
    apply_url: str
    city: str | None = None
    state: str | None = None
    country: str | None = None
    job_category: str | None = None
    job_type: str | None = None
    work_mode: str | None = None
    posted_at: datetime | None = None
    score_breakdown: dict[str, float] | None = None


class MatchResult(MatchSummaryResponse):
    description_html: str
    description_truncated: bool = False


class MatchResponse(BaseModel):
    matches: list[MatchSummaryResponse]
    total: int
    session_id: str
    page: int = 1
    page_size: int
    total_pages: int
    reused_from_cache: bool = False
    fallback: bool = False


class FacetItem(BaseModel):
    """A single facet option with its count."""

    value: str
    label: str
    count: int


class LocationFacetItem(BaseModel):
    """A location in the facet hierarchy."""

    value: str
    label: str
    count: int
    type: str  # "country", "state", "city"
    country: str | None = None
    state: str | None = None
    children: list["LocationFacetItem"] | None = None


class MatchFacetsResponse(BaseModel):
    """Response for match facets calculated from cached results."""

    companies: list[FacetItem]
    categories: list[FacetItem]
    job_types: list[FacetItem]
    work_modes: list[FacetItem]
    locations: list[LocationFacetItem]
    total_matches: int
