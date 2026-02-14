from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


JobSource = Literal[
    "greenhouse", "lever", "linkedin_scrape", "indeed_scrape", "workday", "ashby", "smartrecruiters"
]
JobCategory = Literal[
    "software_engineering",
    "product_management",
    "data_science_ai",
    "quantitative_finance",
    "hardware_engineering",
]


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
    visa_sponsored: bool | None = None
    f1_friendly: bool | None = None
    job_category: JobCategory | None = None
    requires_sponsorship: bool | None = None
    requires_us_citizenship: bool | None = None
    application_closed: bool | None = None
    is_faang_plus: bool | None = None
    requires_advanced_degree: bool | None = None
    description_embedding: list[float] | None = None
