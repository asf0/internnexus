"""jobs sync partial indexes

Adds partial indexes on the jobs table to support the batched sync operations
(mark_inactive, reactivate, delete_inactive). These indexes cover the exact
predicates used by the CTE batch queries and eliminate sequential scans on
the 8+ GB jobs table during sync.

CREATE INDEX CONCURRENTLY is used to avoid blocking writes during index
construction. This requires running outside a transaction, hence the
autocommit_block() calls.

Revision ID: 0002_jobs_sync_indexes
Revises: 0001_initial_schema
Create Date: 2026-06-19 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_jobs_sync_indexes"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACTIVE_PREDICATE = "is_active IS TRUE AND source <> 'manual'::job_source"
_INACTIVE_PREDICATE = "is_active IS FALSE AND source <> 'manual'::job_source"


def upgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.create_index(
            "idx_jobs_active_sync",
            "jobs",
            ["id"],
            unique=False,
            postgresql_concurrently=True,
            postgresql_where=sa.text(_ACTIVE_PREDICATE),
        )
        op.create_index(
            "idx_jobs_inactive_sync",
            "jobs",
            ["id"],
            unique=False,
            postgresql_concurrently=True,
            postgresql_where=sa.text(_INACTIVE_PREDICATE),
        )


def downgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.drop_index("idx_jobs_active_sync", postgresql_concurrently=True)
        op.drop_index("idx_jobs_inactive_sync", postgresql_concurrently=True)
