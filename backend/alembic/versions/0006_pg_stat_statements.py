"""Enable query-level PostgreSQL observability.

Revision ID: 0006_pg_stat_statements
Revises: 0005_search_vector_change_guard
Create Date: 2026-06-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0006_pg_stat_statements"
down_revision: str | None = "0005_search_vector_change_guard"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")


def downgrade() -> None:
    # The extension may have existed before this application migration. It is
    # harmless to older revisions, so never drop a potentially shared object.
    pass
