"""Add job board snapshots and pipeline sync state.

Introduces the shared schema for per-board content snapshots used by the
pipeline's change-detection step, plus a singleton row tracking whether
the snapshot bootstrap has already been run.

Revision ID: 0011_job_board_snapshots
Revises: 0010_location_filter_indexes
Create Date: 2026-07-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_job_board_snapshots"
down_revision: str | None = "0010_location_filter_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    job_source = postgresql.ENUM(name="job_source", create_type=False)
    op.create_table(
        "job_board_snapshots",
        sa.Column("source", job_source, nullable=False),
        sa.Column("company_slug", sa.String(length=128), nullable=False),
        sa.Column("board_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "manifest",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("job_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("source", "company_slug"),
    )

    op.create_table(
        "pipeline_sync_state",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=False),
        sa.Column(
            "snapshots_bootstrapped",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "snapshots_bootstrapped_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        "INSERT INTO pipeline_sync_state (id, snapshots_bootstrapped) VALUES (1, false)"
    )


def downgrade() -> None:
    op.drop_table("pipeline_sync_state")
    op.drop_table("job_board_snapshots")
