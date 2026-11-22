"""Add run-scoped job sightings and id-ordered sync indexes.

Revision ID: 0004_pipeline_job_sightings
Revises: 0003_jobs_last_seen_sync_indexes
Create Date: 2026-06-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_pipeline_job_sightings"
down_revision: str | None = "0003_jobs_last_seen_sync_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACTIVE_PREDICATE = "is_active IS TRUE AND source <> 'manual'::job_source"
_INACTIVE_PREDICATE = "is_active IS FALSE AND source <> 'manual'::job_source"


def upgrade() -> None:
    job_source = postgresql.ENUM(name="job_source", create_type=False)
    op.create_table(
        "pipeline_job_sightings",
        sa.Column("sync_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("source", job_source, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("sync_id", "fingerprint"),
    )

    ctx = op.get_context()
    with ctx.autocommit_block():
        op.create_index(
            "idx_jobs_active_id_sync",
            "jobs",
            ["id"],
            unique=False,
            postgresql_concurrently=True,
            postgresql_where=sa.text(_ACTIVE_PREDICATE),
        )
        op.create_index(
            "idx_jobs_inactive_id_sync",
            "jobs",
            ["id"],
            unique=False,
            postgresql_concurrently=True,
            postgresql_where=sa.text(_INACTIVE_PREDICATE),
        )


def downgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.drop_index("idx_jobs_active_id_sync", postgresql_concurrently=True)
        op.drop_index("idx_jobs_inactive_id_sync", postgresql_concurrently=True)

    op.drop_table("pipeline_job_sightings")
