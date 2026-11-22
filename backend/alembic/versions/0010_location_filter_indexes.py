"""Add B-tree indexes for location columns.

The pipeline's location normalizer filters on state/city/country and the
facet endpoints group by them; without these indexes every statement
sequentially scans the multi-GB jobs table.

Revision ID: 0010_location_filter_indexes
Revises: 0009_embedding_candidate_index
Create Date: 2026-07-12
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0010_location_filter_indexes"
down_revision: str | None = "0009_embedding_candidate_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("idx_jobs_state", "jobs", ["state"])
    op.create_index("idx_jobs_country", "jobs", ["country"])
    op.create_index("idx_jobs_city", "jobs", ["city"])


def downgrade() -> None:
    op.drop_index("idx_jobs_city", table_name="jobs")
    op.drop_index("idx_jobs_country", table_name="jobs")
    op.drop_index("idx_jobs_state", table_name="jobs")
