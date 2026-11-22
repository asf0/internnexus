"""Add HNSW vector indexes and B-tree filter indexes.

Revision ID: 0008_performance_indexes
Revises: 0007_jobs_id_sync_contract
Create Date: 2026-07-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0008_performance_indexes"
down_revision: str | None = "0007_jobs_id_sync_contract"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_HNSW_M = 16
_HNSW_EF_CONSTRUCTION = 200


def upgrade() -> None:
    op.execute(
        "CREATE INDEX idx_jobs_embedding_hnsw ON jobs "
        "USING hnsw ((description_embedding::halfvec(2560)) halfvec_cosine_ops) "
        f"WITH (m = {_HNSW_M}, ef_construction = {_HNSW_EF_CONSTRUCTION})"
    )
    op.execute(
        "CREATE INDEX idx_resumes_embedding_hnsw ON user_resumes "
        "USING hnsw ((resume_embedding::halfvec(2560)) halfvec_cosine_ops) "
        f"WITH (m = {_HNSW_M}, ef_construction = {_HNSW_EF_CONSTRUCTION})"
    )

    op.create_index("idx_jobs_posted_at", "jobs", ["posted_at"])

    op.create_index("idx_jobs_category", "jobs", ["job_category"])


def downgrade() -> None:
    op.drop_index("idx_jobs_category", table_name="jobs")
    op.drop_index("idx_jobs_posted_at", table_name="jobs")

    op.execute("DROP INDEX IF EXISTS idx_resumes_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_jobs_embedding_hnsw")
