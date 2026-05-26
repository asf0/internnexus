from __future__ import annotations

from datetime import datetime
import enum
import uuid
from typing import ClassVar

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy.sql import func

from app.db import Base

JOBS_ID_FK = "jobs.id"
USERS_ID_FK = "users.id"


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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fingerprint: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    source: Mapped[JobSource] = mapped_column(Enum(JobSource, name="job_source"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    company: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)
    apply_url: Mapped[str] = mapped_column(String, nullable=False)
    description_text: Mapped[str] = mapped_column(Text, nullable=False)
    description_embedding: Mapped[list[float] | None] = mapped_column(Vector(2560), nullable=True)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    job_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    job_type: Mapped[JobType | None] = mapped_column(Enum(JobType, name="job_type"), nullable=True)
    work_mode: Mapped[WorkMode | None] = mapped_column(
        Enum(WorkMode, name="work_mode"), nullable=True
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    clicks: Mapped[list[JobClick]] = relationship(
        "JobClick", back_populates="job", cascade="all, delete-orphan"
    )
    saved_by_users: Mapped[list[SavedJob]] = relationship(
        "SavedJob", back_populates="job", cascade="all, delete-orphan"
    )
    applied_by_users: Mapped[list[AppliedJob]] = relationship(
        "AppliedJob", back_populates="job", cascade="all, delete-orphan"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    image: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    hashed_password: Mapped[str | None] = mapped_column(String, nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_title: Mapped[str | None] = mapped_column(String, nullable=True)
    company: Mapped[str | None] = mapped_column(String, nullable=True)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    skills: Mapped[str | None] = mapped_column(String, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String, nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String, nullable=True)
    preferred_locations: Mapped[str | None] = mapped_column(String, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Kept out of ORM mapping for compatibility with test databases
    # that have not yet added these columns.
    notes: ClassVar[str | None] = None
    last_login_at: ClassVar[datetime | None] = None

    accounts: Mapped[list[Account]] = relationship(
        "Account", back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list[Session]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    password_history: Mapped[list[PasswordHistory]] = relationship(
        "PasswordHistory",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="PasswordHistory.created_at.desc()",
    )
    admin: Mapped[Admin | None] = relationship(
        "Admin",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="[Admin.user_id]",
    )
    job_clicks: Mapped[list[JobClick]] = relationship(
        "JobClick", back_populates="user", cascade="all, delete-orphan"
    )
    resume: Mapped[UserResume | None] = relationship(
        "UserResume",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    notifications: Mapped[list[UserNotification]] = relationship(
        "UserNotification", back_populates="user", cascade="all, delete-orphan"
    )
    saved_jobs: Mapped[list[SavedJob]] = relationship(
        "SavedJob", back_populates="user", cascade="all, delete-orphan"
    )
    applied_jobs: Mapped[list[AppliedJob]] = relationship(
        "AppliedJob", back_populates="user", cascade="all, delete-orphan"
    )


class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(JOBS_ID_FK, ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship("User", back_populates="saved_jobs")
    job: Mapped[Job] = relationship("Job", back_populates="saved_by_users")

    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uix_saved_jobs_user_job"),)


class UserResume(Base):
    __tablename__ = "user_resumes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"), unique=True, nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="ready")
    encrypted_resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    resume_embedding: Mapped[list[float] | None] = mapped_column(Vector(2560), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    embedding_dim: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_embedded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    embedding_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship("User", back_populates="resume")


class AppliedJob(Base):
    __tablename__ = "applied_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(JOBS_ID_FK, ondelete="CASCADE"), nullable=False
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship("User", back_populates="applied_jobs")
    job: Mapped[Job] = relationship("Job", back_populates="applied_by_users")

    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uix_applied_jobs_user_job"),)


class UserNotification(Base):
    __tablename__ = "user_notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="notifications")


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"), unique=True, nullable=False
    )
    role: Mapped[AdminRole] = mapped_column(
        Enum(AdminRole, name="admin_role"),
        nullable=False,
        default=AdminRole.admin,
        server_default="admin",
    )
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="SET NULL"), nullable=True
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(
        "User", back_populates="admin", foreign_keys="[Admin.user_id]"
    )




class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="SET NULL"), nullable=True, index=True
    )
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )


class JobClick(Base):
    __tablename__ = "job_clicks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(JOBS_ID_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="SET NULL"), nullable=True
    )
    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    utm_source: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="internnexus"
    )
    utm_medium: Mapped[str | None] = mapped_column(String(50), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    referer: Mapped[str | None] = mapped_column(String(500), nullable=True)

    job: Mapped[Job] = relationship("Job", back_populates="clicks")
    user: Mapped[User | None] = relationship("User", back_populates="job_clicks")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String, nullable=False)
    provider_account_id: Mapped[str] = mapped_column(String, nullable=False)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_type: Mapped[str | None] = mapped_column(String, nullable=True)
    scope: Mapped[str | None] = mapped_column(String, nullable=True)
    id_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_state: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship("User", back_populates="accounts")

    __table_args__ = (
        UniqueConstraint("provider", "provider_account_id", name="uix_provider_account"),
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship("User", back_populates="sessions")


class VerificationToken(Base):
    __tablename__ = "verification_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identifier: Mapped[str] = mapped_column(String, nullable=False)
    token: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("identifier", "token", name="uix_identifier_token"),)


class PasswordHistory(Base):
    __tablename__ = "password_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"), nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship("User", back_populates="password_history")


class PipelineRunStatus(enum.Enum):
    running = "running"
    completed = "completed"
    failed = "failed"


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[PipelineRunStatus] = mapped_column(
        Enum(PipelineRunStatus, name="pipeline_run_status"),
        nullable=False,
        server_default=PipelineRunStatus.running.value,
    )
    step_completed: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_step: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    results: Mapped[str | None] = mapped_column(Text, nullable=True)


class PipelineCommandStatus(enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class PipelineCommand(Base):
    __tablename__ = "pipeline_commands"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[PipelineCommandStatus] = mapped_column(
        Enum(PipelineCommandStatus, name="pipeline_command_status"),
        nullable=False,
        server_default=PipelineCommandStatus.pending.value,
    )
    step: Mapped[str | None] = mapped_column(String, nullable=True)
    skip_discover: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    process_all: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    test_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="SET NULL"), nullable=True
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
