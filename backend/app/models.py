from __future__ import annotations

import enum
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from .db import Base


class JobSource(enum.Enum):
    greenhouse = "greenhouse"
    lever = "lever"
    linkedin_scrape = "linkedin_scrape"
    indeed_scrape = "indeed_scrape"


class JobCategory(enum.Enum):
    software_engineering = "software_engineering"
    product_management = "product_management"
    data_science_ai = "data_science_ai"
    quantitative_finance = "quantitative_finance"
    hardware_engineering = "hardware_engineering"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fingerprint = Column(String, nullable=False, unique=True, index=True)
    source = Column(Enum(JobSource, name="job_source"), nullable=False)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String, nullable=False)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True)
    apply_url = Column(String, nullable=False)
    description_text = Column(Text, nullable=False)
    description_embedding = Column(Vector(768))  # nomic-embed-text dimensions
    visa_sponsored = Column(Boolean, nullable=True)
    f1_friendly = Column(Boolean, nullable=True)
    job_category = Column(Enum(JobCategory, name="job_category"), nullable=True)
    requires_sponsorship = Column(Boolean, nullable=True, server_default="false")
    requires_us_citizenship = Column(Boolean, nullable=True, server_default="false")
    application_closed = Column(Boolean, nullable=True, server_default="false")
    is_faang_plus = Column(Boolean, nullable=True, server_default="false")
    requires_advanced_degree = Column(Boolean, nullable=True, server_default="false")
    posted_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    last_seen = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
