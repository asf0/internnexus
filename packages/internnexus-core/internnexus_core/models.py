"""ORM mappings for tables shared by the backend and ingestion pipeline.

These mappings intentionally contain only tables both services own. Backend
relationships to user-facing tables are attached in ``app.models`` so the
pipeline can use the same table definitions without importing backend code.
"""

from __future__ import annotations

from datetime import datetime
import enum
import uuid

from pgvector.sqlalchemy import HALFVEC
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

from internnexus_core.jobs import JobSource, JobType, WorkMode


class Base(DeclarativeBase):
    """Single metadata registry for ORM tables shared across services."""


class PipelineRunStatus(enum.Enum):
    running = "running"
    completed = "completed"
    failed = "failed"


class PipelineCommandStatus(enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


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
    description_embedding: Mapped[list[float] | None] = mapped_column(HALFVEC(1024), nullable=True, deferred=True)
    embedding_input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    embedding_skip_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    embedding_skipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    job_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    job_type: Mapped[JobType | None] = mapped_column(Enum(JobType, name="job_type"), nullable=True)
    work_mode: Mapped[WorkMode | None] = mapped_column(Enum(WorkMode, name="work_mode"), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PipelineJobSighting(Base):
    """Narrow run-scoped record proving that an upstream job was observed."""

    __tablename__ = "pipeline_job_sightings"

    sync_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[JobSource] = mapped_column(Enum(JobSource, name="job_source"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


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
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    results: Mapped[str | None] = mapped_column(Text, nullable=True)


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
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class JobBoardSnapshot(Base):
    """Per-board snapshot of the observed job listing manifest.

    The composite primary key ``(source, company_slug)`` identifies a single
    board instance. ``board_hash`` stores a stable digest of the board's
    job fingerprint set so the pipeline can detect content changes without
    re-scanning every row; when it changes, ``changed_at`` is updated.
    """

    __tablename__ = "job_board_snapshots"

    source: Mapped[JobSource] = mapped_column(
        Enum(JobSource, name="job_source"), primary_key=True, nullable=False
    )
    company_slug: Mapped[str] = mapped_column(String(128), primary_key=True, nullable=False)
    board_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    job_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PipelineSyncState(Base):
    """Singleton row tracking cross-step pipeline sync bookkeeping.

    Only row ``id=1`` is expected to exist; the migration seeds it. Future
    sync steps (e.g. board snapshot bootstrap) flip boolean flags here so
    they are not re-run on every pipeline invocation.
    """

    __tablename__ = "pipeline_sync_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    snapshots_bootstrapped: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    snapshots_bootstrapped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
