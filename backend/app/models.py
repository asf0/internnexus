from __future__ import annotations

import enum
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
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


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True, index=True)
    email_verified = Column(Boolean, nullable=False, server_default="false")
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    image = Column(String, nullable=True)  # Avatar URL
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Authentication
    hashed_password = Column(String, nullable=True)  # Null for OAuth-only users

    # Profile Information
    bio = Column(Text, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)

    # Professional Information
    job_title = Column(String, nullable=True)
    company = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    skills = Column(String, nullable=True)  # JSON array as string
    linkedin_url = Column(String, nullable=True)
    portfolio_url = Column(String, nullable=True)
    preferred_locations = Column(String, nullable=True)  # JSON array as string

    # Account Status
    is_deleted = Column(Boolean, nullable=False, server_default="false")
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String, nullable=False)  # github, google, credentials
    provider_account_id = Column(String, nullable=False)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    token_type = Column(String, nullable=True)
    scope = Column(String, nullable=True)
    id_token = Column(Text, nullable=True)
    session_state = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="accounts")

    # Unique constraint on provider + provider_account_id
    __table_args__ = (
        UniqueConstraint("provider", "provider_account_id", name="uix_provider_account"),
    )


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="sessions")


class VerificationToken(Base):
    __tablename__ = "verification_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identifier = Column(String, nullable=False)  # Usually email
    token = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Unique constraint on identifier + token
    __table_args__ = (UniqueConstraint("identifier", "token", name="uix_identifier_token"),)
