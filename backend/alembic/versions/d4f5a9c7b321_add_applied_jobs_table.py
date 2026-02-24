"""add applied jobs table

Revision ID: d4f5a9c7b321
Revises: c1d3e7f9a4b2
Create Date: 2026-02-24 00:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "d4f5a9c7b321"
down_revision = "c1d3e7f9a4b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "applied_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "job_id", name="uix_applied_jobs_user_job"),
    )
    op.create_index(op.f("ix_applied_jobs_user_id"), "applied_jobs", ["user_id"], unique=False)
    op.create_index(op.f("ix_applied_jobs_job_id"), "applied_jobs", ["job_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_applied_jobs_job_id"), table_name="applied_jobs")
    op.drop_index(op.f("ix_applied_jobs_user_id"), table_name="applied_jobs")
    op.drop_table("applied_jobs")
