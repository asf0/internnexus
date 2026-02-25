from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


JobSource = Literal[
    "greenhouse",
    "lever",
    "ashby",
    "linkedin_scrape",
    "indeed_scrape",
]
JobType = Literal["internship", "full_time", "part_time"]
WorkMode = Literal["remote", "hybrid", "on_site"]


class JobSchema(BaseModel):
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

    # External IDs
    external_id: str | None = None
    internal_job_id: int | None = None
    requisition_id: str | None = None

    # Job Details
    education: str | None = None
    language: str | None = None
    commitment: str | None = None
    department: str | None = None
    team: str | None = None
    employment_type: str | None = None

    # Location Extended
    all_locations: list[str] | None = None
    location_raw: str | None = None
    secondary_locations: list[dict] | None = None
    workplace_type: str | None = None
    is_remote: bool | None = None

    # Address (Ashby)
    address_region: str | None = None
    address_country: str | None = None
    address_locality: str | None = None
    address_raw: dict | None = None

    # Timestamps Extended
    first_published: datetime | None = None
    updated_at: datetime | None = None
    created_at_raw: int | None = None

    # Salary (Lever)
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_interval: str | None = None
    salary_description: str | None = None
    salary_description_plain: str | None = None

    # Content Variants
    description_html: str | None = None
    description_plain: str | None = None
    description_body_html: str | None = None
    description_body_plain: str | None = None
    opening_html: str | None = None
    opening_plain: str | None = None
    additional_html: str | None = None
    additional_plain: str | None = None

    # Requirements (Lever)
    requirements: list[dict] | None = None
    requirements_html: str | None = None
    requirements_plain: str | None = None
    has_requirements: bool | None = None
    requirements_count: int | None = None

    # Metadata Arrays (GH)
    departments: list[dict] | None = None
    offices: list[dict] | None = None
    data_compliance: list[dict] | None = None
    metadata: list[dict] | None = None

    # Compensation (Ashby)
    compensation: dict | None = None
    is_listed: bool | None = None
    should_display_compensation: bool | None = None

    # URLs
    hosted_url: str | None = None
    job_url: str | None = None
    company_name: str | None = None


class GreenhouseJobMetadataSchema(BaseModel):
    external_id: str
    internal_job_id: int
    requisition_id: str
    education: str | None = None
    language: str = "en"
    first_published: datetime
    updated_at: datetime
    departments: list[dict] = Field(default_factory=list)
    offices: list[dict] = Field(default_factory=list)
    data_compliance: list[dict] = Field(default_factory=list)
    hosted_url: str


class LeverJobMetadataSchema(BaseModel):
    external_id: str
    commitment: str
    department: str
    team: str
    all_locations: list[str] = Field(default_factory=list)
    workplace_type: str
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_interval: str | None = None
    salary_description: str | None = None
    description_html: str
    description_plain: str
    requirements: list[dict] = Field(default_factory=list)
    requirements_html: str | None = None
    requirements_plain: str | None = None
    has_requirements: bool = False
    hosted_url: str
    created_at_raw: int


class AshbyJobMetadataSchema(BaseModel):
    external_id: str
    department: str
    team: str
    employment_type: str
    location_raw: str
    address_locality: str
    address_region: str
    address_country: str
    is_remote: bool | None = None
    description_html: str
    description_plain: str
    job_url: str
    compensation: dict = Field(default_factory=dict)
    is_listed: bool = True
    updated_at: datetime
