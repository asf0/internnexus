from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


JobSource = Literal["greenhouse", "lever", "ashby", "manual"]
JobType = Literal["internship", "full_time", "part_time"]
WorkMode = Literal["remote", "hybrid", "on_site"]


class JobSchema(BaseModel):
    """Normalised job posting schema — fields persisted to the jobs table."""

    model_config = ConfigDict(extra="ignore")

    source: JobSource
    title: str
    company: str
    location: str
    city: str | None = None
    state: str | None = None
    country: str | None = None
    apply_url: str
    description_text: str
    posted_at: datetime | None = None
    job_category: str | None = None
    job_type: JobType | None = None
    work_mode: WorkMode | None = None
    description_embedding: list[float] | None = None

    @field_validator("apply_url")
    @classmethod
    def require_apply_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("apply_url must not be empty")
        return normalized
