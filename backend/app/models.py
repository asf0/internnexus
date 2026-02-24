from __future__ import annotations

import enum
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .db import Base


class JobSource(enum.Enum):
    greenhouse = "greenhouse"
    lever = "lever"
    ashby = "ashby"
    manual = "manual"


class JobType(enum.Enum):
    internship = "internship"
    full_time = "full_time"
    part_time = "part_time"


class WorkMode(enum.Enum):
    remote = "remote"
    hybrid = "hybrid"
    on_site = "on_site"


class AdminRole(enum.Enum):
    admin = "admin"
    super_admin = "super_admin"


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
    description_embedding = Column(Vector(1024), nullable=True)
    search_vector = Column(TSVECTOR, nullable=True)
    job_category = Column(String(100), nullable=True)
    job_type = Column(Enum(JobType, name="job_type"), nullable=True)
    work_mode = Column(Enum(WorkMode, name="work_mode"), nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    last_seen = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    greenhouse_metadata = relationship(
        "GreenhouseJobMetadata", back_populates="job", uselist=False, cascade="all, delete-orphan"
    )
    lever_metadata = relationship(
        "LeverJobMetadata", back_populates="job", uselist=False, cascade="all, delete-orphan"
    )
    ashby_metadata = relationship(
        "AshbyJobMetadata", back_populates="job", uselist=False, cascade="all, delete-orphan"
    )
    clicks = relationship("JobClick", back_populates="job", cascade="all, delete-orphan")
    saved_by_users = relationship("SavedJob", back_populates="job", cascade="all, delete-orphan")
    applied_by_users = relationship("AppliedJob", back_populates="job", cascade="all, delete-orphan")


class GreenhouseJobMetadata(Base):
    __tablename__ = "greenhouse_job_metadata"

    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    external_id = Column(String, nullable=False)
    internal_job_id = Column(BigInteger, nullable=False)
    requisition_id = Column(String, nullable=True)
    education = Column(String, nullable=True)
    language = Column(String, nullable=False, server_default="en")
    first_published = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    departments = Column(JSONB, nullable=False, server_default="[]")
    offices = Column(JSONB, nullable=False, server_default="[]")
    data_compliance = Column(JSONB, nullable=False, server_default="[]")
    hosted_url = Column(String, nullable=False)

    job = relationship("Job", back_populates="greenhouse_metadata")


class LeverJobMetadata(Base):
    __tablename__ = "lever_job_metadata"

    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    external_id = Column(String, nullable=False)
    commitment = Column(String, nullable=True)
    department = Column(String, nullable=True)
    team = Column(String, nullable=True)
    all_locations = Column(JSONB, nullable=False, server_default="[]")
    workplace_type = Column(String, nullable=False)
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    salary_currency = Column(String, nullable=True)
    salary_interval = Column(String, nullable=True)
    salary_description = Column(Text, nullable=True)
    description_html = Column(Text, nullable=False)
    description_plain = Column(Text, nullable=False)
    requirements = Column(JSONB, nullable=False, server_default="[]")
    requirements_html = Column(Text, nullable=True)
    requirements_plain = Column(Text, nullable=True)
    has_requirements = Column(Boolean, nullable=False, server_default="false")
    hosted_url = Column(String, nullable=False)
    created_at_raw = Column(BigInteger, nullable=False)

    job = relationship("Job", back_populates="lever_metadata")


class AshbyJobMetadata(Base):
    __tablename__ = "ashby_job_metadata"

    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    external_id = Column(String, nullable=False)
    department = Column(String, nullable=True)
    team = Column(String, nullable=True)
    employment_type = Column(String, nullable=True)
    location_raw = Column(String, nullable=True)
    address_locality = Column(String, nullable=True)
    address_region = Column(String, nullable=True)
    address_country = Column(String, nullable=True)
    is_remote = Column(Boolean, nullable=True)
    description_html = Column(Text, nullable=True)
    description_plain = Column(Text, nullable=True)
    job_url = Column(String, nullable=False)
    compensation = Column(JSONB, nullable=True)
    is_listed = Column(Boolean, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    job = relationship("Job", back_populates="ashby_metadata")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True, index=True)
    email_verified = Column(Boolean, nullable=False, server_default="false")
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    image = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    hashed_password = Column(String, nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)

    bio = Column(Text, nullable=True)
    job_title = Column(String, nullable=True)
    company = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    skills = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    portfolio_url = Column(String, nullable=True)
    preferred_locations = Column(String, nullable=True)

    is_deleted = Column(Boolean, nullable=False, server_default="false")
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text, nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    password_history = relationship(
        "PasswordHistory",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="PasswordHistory.created_at.desc()",
    )
    admin = relationship(
        "Admin",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="[Admin.user_id]",
    )
    job_clicks = relationship("JobClick", back_populates="user", cascade="all, delete-orphan")
    resume = relationship(
        "UserResume",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    notifications = relationship("UserNotification", back_populates="user", cascade="all, delete-orphan")
    saved_jobs = relationship("SavedJob", back_populates="user", cascade="all, delete-orphan")
    applied_jobs = relationship("AppliedJob", back_populates="user", cascade="all, delete-orphan")


class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="saved_jobs")
    job = relationship("Job", back_populates="saved_by_users")

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uix_saved_jobs_user_job"),
    )


class UserResume(Base):
    __tablename__ = "user_resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    file_name = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)
    status = Column(String(50), nullable=False, server_default="ready")
    uploaded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="resume")


class AppliedJob(Base):
    __tablename__ = "applied_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    applied_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="applied_jobs")
    job = relationship("Job", back_populates="applied_by_users")

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uix_applied_jobs_user_job"),
    )


class UserNotification(Base):
    __tablename__ = "user_notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(80), nullable=False)
    payload = Column(JSONB, nullable=False, server_default="{}")
    is_read = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="notifications")


class Admin(Base):
    __tablename__ = "admins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    role = Column(
        Enum(AdminRole, name="admin_role"), nullable=False, default="admin", server_default="admin"
    )
    granted_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    granted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="admin", foreign_keys="[Admin.user_id]")


class JobClick(Base):
    __tablename__ = "job_clicks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    clicked_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    utm_source = Column(String(50), nullable=False, server_default="internnexus")
    utm_medium = Column(String(50), nullable=True)
    utm_campaign = Column(String(100), nullable=True)
    ip_hash = Column(String(64), nullable=True)
    user_agent = Column(String(500), nullable=True)
    referer = Column(String(500), nullable=True)

    job = relationship("Job", back_populates="clicks")
    user = relationship("User", back_populates="job_clicks")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String, nullable=False)
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

    user = relationship("User", back_populates="accounts")

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

    user = relationship("User", back_populates="sessions")


class VerificationToken(Base):
    __tablename__ = "verification_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identifier = Column(String, nullable=False)
    token = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("identifier", "token", name="uix_identifier_token"),)


class PasswordHistory(Base):
    __tablename__ = "password_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="password_history")


class PipelineRunStatus(enum.Enum):
    running = "running"
    completed = "completed"
    failed = "failed"


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(
        Enum(PipelineRunStatus, name="pipeline_run_status"),
        nullable=False,
        server_default="running",
    )
    step_completed = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    error_step = Column(String, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    results = Column(Text, nullable=True)
