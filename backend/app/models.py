from __future__ import annotations

from datetime import datetime
import enum
import uuid

from pgvector.sqlalchemy import HALFVEC
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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy.sql import func

from app.infra.db import Base
from internnexus_core.jobs import JobSource, JobType, WorkMode  # noqa: F401
from internnexus_core.models import (
    Job,
    JobBoardSnapshot,
    PipelineCommand,
    PipelineCommandStatus,
    PipelineJobSighting,
    PipelineRun,
    PipelineRunStatus,
    PipelineSyncState,
)  # noqa: F401

JOBS_ID_FK = "jobs.id"
USERS_ID_FK = "users.id"
DELETE_ORPHAN_CASCADE = "all, delete-orphan"
SET_NULL = "SET NULL"

__all__ = [
    "Account",
    "Admin",
    "AdminAuditLog",
    "AdminRole",
    "AppliedJob",
    "Base",
    "Job",
    "JobBoardSnapshot",
    "JobClick",
    "MCPApiKey",
    "MCPInvocation",
    "JobSource",
    "JobType",
    "PasswordHistory",
    "PipelineCommand",
    "PipelineCommandStatus",
    "PipelineJobSighting",
    "PipelineRun",
    "PipelineRunStatus",
    "PipelineSyncState",
    "SavedJob",
    "Session",
    "User",
    "UserNotification",
    "UserResume",
    "WorkMode",
]


class AdminRole(enum.Enum):
    admin = "admin"
    super_admin = "super_admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    image: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    hashed_password: Mapped[str | None] = mapped_column(String, nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    accounts: Mapped[list[Account]] = relationship("Account", back_populates="user", cascade=DELETE_ORPHAN_CASCADE)
    sessions: Mapped[list[Session]] = relationship("Session", back_populates="user", cascade=DELETE_ORPHAN_CASCADE)
    password_history: Mapped[list[PasswordHistory]] = relationship(
        "PasswordHistory",
        back_populates="user",
        cascade=DELETE_ORPHAN_CASCADE,
        order_by="PasswordHistory.created_at.desc()",
    )
    admin: Mapped[Admin | None] = relationship(
        "Admin",
        back_populates="user",
        uselist=False,
        cascade=DELETE_ORPHAN_CASCADE,
        foreign_keys="[Admin.user_id]",
    )
    job_clicks: Mapped[list[JobClick]] = relationship("JobClick", back_populates="user", cascade=DELETE_ORPHAN_CASCADE)
    resume: Mapped[UserResume | None] = relationship(
        "UserResume",
        back_populates="user",
        uselist=False,
        cascade=DELETE_ORPHAN_CASCADE,
    )
    notifications: Mapped[list[UserNotification]] = relationship(
        "UserNotification", back_populates="user", cascade=DELETE_ORPHAN_CASCADE
    )
    saved_jobs: Mapped[list[SavedJob]] = relationship("SavedJob", back_populates="user", cascade=DELETE_ORPHAN_CASCADE)
    applied_jobs: Mapped[list[AppliedJob]] = relationship(
        "AppliedJob", back_populates="user", cascade=DELETE_ORPHAN_CASCADE
    )
    mcp_api_keys: Mapped[list[MCPApiKey]] = relationship(
        "MCPApiKey", back_populates="user", cascade=DELETE_ORPHAN_CASCADE
    )


class MCPApiKey(Base):
    """A user-scoped MCP credential. The plaintext secret is never stored."""

    __tablename__ = "mcp_api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="mcp_api_keys")


class MCPInvocation(Base):
    """Retention-safe analytics for an MCP tool invocation."""

    __tablename__ = "mcp_invocations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete=SET_NULL), nullable=True, index=True
    )
    mcp_api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mcp_api_keys.id", ondelete=SET_NULL), nullable=True, index=True
    )
    tool_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    invoked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(JOBS_ID_FK, ondelete=SET_NULL), nullable=True, index=True
    )
    result_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")


class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(JOBS_ID_FK, ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

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
    resume_embedding: Mapped[list[float] | None] = mapped_column(HALFVEC(1024), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    embedding_dim: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_embedded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    embedding_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
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
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
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
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete=SET_NULL), nullable=True
    )
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="admin", foreign_keys="[Admin.user_id]")


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete=SET_NULL), nullable=True, index=True
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
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete=SET_NULL), nullable=True
    )
    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    utm_source: Mapped[str] = mapped_column(String(50), nullable=False, server_default="internnexus")
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship("User", back_populates="accounts")

    __table_args__ = (UniqueConstraint("provider", "provider_account_id", name="uix_provider_account"),)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"), nullable=False
    )
    jti: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="sessions")


class PasswordHistory(Base):
    __tablename__ = "password_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"), nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="password_history")


Job.clicks = relationship("JobClick", back_populates="job", cascade=DELETE_ORPHAN_CASCADE)
Job.saved_by_users = relationship("SavedJob", back_populates="job", cascade=DELETE_ORPHAN_CASCADE)
Job.applied_by_users = relationship("AppliedJob", back_populates="job", cascade=DELETE_ORPHAN_CASCADE)
