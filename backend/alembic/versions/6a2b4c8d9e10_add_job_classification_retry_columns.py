"""add job classification retry columns

Revision ID: 6a2b4c8d9e10
Revises: 3f7c2a9d4b12
Create Date: 2026-02-24 18:05:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6a2b4c8d9e10"
down_revision = "3f7c2a9d4b12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("classification_attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("jobs", sa.Column("classification_last_attempt_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("classification_next_retry_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("classification_last_error", sa.Text(), nullable=True))
    op.create_index(
        op.f("ix_jobs_classification_next_retry_at"),
        "jobs",
        ["classification_next_retry_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_jobs_classification_next_retry_at"), table_name="jobs")
    op.drop_column("jobs", "classification_last_error")
    op.drop_column("jobs", "classification_next_retry_at")
    op.drop_column("jobs", "classification_last_attempt_at")
    op.drop_column("jobs", "classification_attempts")
