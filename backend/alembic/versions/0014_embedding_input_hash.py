"""Track the normalized input used for job embeddings.

Revision ID: 0014_embedding_input_hash
Revises: 0013_mcp_invocation_analytics
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0014_embedding_input_hash"
down_revision: str | None = "0013_mcp_invocation_analytics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CANDIDATE_PREDICATE = (
    "is_active AND description_embedding IS NULL AND embedding_skip_reason IS NULL"
)


def upgrade() -> None:
    op.add_column("jobs", sa.Column("embedding_input_hash", sa.String(length=64), nullable=True))
    op.drop_index("idx_jobs_needs_embedding", table_name="jobs")
    op.execute(
        f"CREATE INDEX idx_jobs_needs_embedding ON jobs (id) WHERE {_CANDIDATE_PREDICATE}"
    )


def downgrade() -> None:
    op.drop_index("idx_jobs_needs_embedding", table_name="jobs")
    op.execute(
        "CREATE INDEX idx_jobs_needs_embedding ON jobs (id) "
        "WHERE description_embedding IS NULL AND embedding_skip_reason IS NULL"
    )
    op.drop_column("jobs", "embedding_input_hash")
