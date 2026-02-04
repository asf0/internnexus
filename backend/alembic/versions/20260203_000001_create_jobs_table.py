"""create jobs table

Revision ID: 20260203_000001
Revises: 
Create Date: 2026-02-03 00:00:01.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = "20260203_000001"
down_revision = None
branch_labels = None
depends_on = None


job_source_enum = sa.Enum(
    "greenhouse",
    "lever",
    "linkedin_scrape",
    "indeed_scrape",
    name="job_source",
)


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("source", job_source_enum, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("company", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("apply_url", sa.String(), nullable=False),
        sa.Column("description_text", sa.Text(), nullable=False),
        sa.Column("description_embedding", Vector(1536), nullable=True),
        sa.Column("visa_sponsored", sa.Boolean(), nullable=True),
        sa.Column("f1_friendly", sa.Boolean(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_jobs_fingerprint", "jobs", ["fingerprint"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_jobs_fingerprint", table_name="jobs")
    op.drop_table("jobs")
    job_source_enum.drop(op.get_bind(), checkfirst=True)
