from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field


class AdminUserResponse(BaseModel):
    """Schema for admin user listing response."""

    id: UUID
    email: str
    name: str | None
    is_active: bool
    created_at: datetime
    has_password: bool
    admin_role: str | None = None
    provider: str | None = None
    notes: str | None = None

    model_config = {"from_attributes": True}


class UserCreateRequest(BaseModel):
    """Schema for user creation request."""

    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8)
    name: str | None = Field(None, max_length=255)


class UserNotesUpdateRequest(BaseModel):
    """Schema for user notes update request."""

    notes: str | None = None


class AdminJobResponse(BaseModel):
    """Schema for admin job listing response with click tracking."""

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
    job_category: str | None = None
    job_type: str | None = None
    work_mode: str | None = None
    posted_at: datetime | None = None
    is_active: bool
    click_count: int = 0
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class AdminJobUpdateRequest(BaseModel):
    """Schema for admin job update request."""

    title: str | None = None
    company: str | None = None
    location: str | None = None
    job_category: str | None = None
    job_type: str | None = None
    work_mode: str | None = None
    is_active: bool | None = None


T = TypeVar("T")


class AdminListResponse(BaseModel, Generic[T]):
    """Generic paginated list response for admin endpoints."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class ClickStatsResponse(BaseModel):
    """Schema for click statistics response."""

    total_clicks: int
    clicks_today: int
    clicks_this_week: int
    clicks_this_month: int
    authenticated_clicks_total: int
    anonymous_clicks_total: int
    unique_users_total: int
    unique_jobs_total: int
    clicks_last_24h: int
    avg_clicks_per_day_30d: float
    top_sources: list[dict]
    top_mediums: list[dict]
    top_campaigns: list[dict]
    clicks_by_hour_today: list["HourlyClicks"]
    daily_breakdown_14d: list[dict]
    top_jobs: list[dict]


class HourlyClicks(BaseModel):
    """Schema for hourly click counts."""

    hour: int
    clicks: int


class TopJobByClicks(BaseModel):
    """Schema for top job by clicks."""

    job_id: UUID
    title: str
    company: str
    apply_url: str | None = None
    click_count: int


class DayClickStatsResponse(BaseModel):
    """Schema for detailed click statistics for a specific date."""

    date: str  # YYYY-MM-DD format
    total_clicks: int
    unique_jobs: int
    unique_users: int
    anonymous_clicks: int
    clicks_by_hour: list[HourlyClicks]
    top_jobs: list[TopJobByClicks]


class JobClickResponse(BaseModel):
    """Schema for individual job click response."""

    id: UUID
    job_id: UUID
    job_title: str
    company: str
    apply_url: str | None = None
    user_id: UUID | None = None
    user_email: str | None = None
    user_name: str | None = None
    clicked_at: datetime
    utm_source: str
    utm_medium: str | None = None
    utm_campaign: str | None = None

    model_config = {"from_attributes": True}


class PipelineRunResponse(BaseModel):
    """Schema for pipeline run response."""

    id: UUID
    status: str
    step_completed: str | None = None
    error_message: str | None = None
    error_step: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    results: str | None = None

    model_config = {"from_attributes": True}


class ClicksByUserResponse(BaseModel):
    """Schema for clicks aggregated by user."""

    user_id: UUID | None
    email: str | None  # null for anonymous clicks
    name: str | None
    click_count: int


class AdminJobCreateRequest(BaseModel):
    """Schema for admin job creation request."""

    title: str = Field(..., min_length=1, max_length=500)
    company: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=500)
    apply_url: str = Field(..., min_length=1, max_length=2000)
    description_text: str = Field(..., min_length=1)
    job_category: str | None = Field(None, max_length=100)
    job_type: str | None = None  # internship, full_time, part_time
    work_mode: str | None = None  # remote, hybrid, on_site
    posted_at: datetime | None = None


class AdminJobBulkRequest(BaseModel):
    """Schema for bulk job actions request."""

    job_ids: list[UUID] = Field(..., min_length=1)
    action: str  # "activate", "deactivate", "delete"
