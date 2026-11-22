"""Add partial index for embedding candidate queries.

Revision ID: 0009_embedding_candidate_index
Revises: 0008_performance_indexes
Create Date: 2026-07-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0009_embedding_candidate_index"
down_revision: str | None = "0008_performance_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CANDIDATE_PREDICATE = (
    "description_embedding IS NULL AND embedding_skip_reason IS NULL"
)


def upgrade() -> None:
    op.execute(
        f"CREATE INDEX idx_jobs_needs_embedding ON jobs (id) "
        f"WHERE {_CANDIDATE_PREDICATE}"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_jobs_needs_embedding")
