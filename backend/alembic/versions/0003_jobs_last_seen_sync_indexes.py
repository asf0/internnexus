"""jobs last_seen sync indexes

Replaces the partial sync indexes from 0002 with composite indexes that
include last_seen. The new sync model marks jobs stale based on
`last_seen < batch_start_time` instead of flipping every row at the start
of the run, so the indexes must cover the stale predicate.

CREATE INDEX CONCURRENTLY is used to avoid blocking writes during index
construction. This requires running outside a transaction, hence the
autocommit_block() calls.

Revision ID: 0003_jobs_last_seen_sync_indexes
Revises: 0002_jobs_sync_indexes
Create Date: 2026-06-20 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_jobs_last_seen_sync_indexes"
down_revision: str | None = "0002_jobs_sync_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACTIVE_PREDICATE = "is_active IS TRUE AND source <> 'manual'::job_source"
_INACTIVE_PREDICATE = "is_active IS FALSE AND source <> 'manual'::job_source"


def upgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.drop_index("idx_jobs_active_sync", postgresql_concurrently=True)
        op.drop_index("idx_jobs_inactive_sync", postgresql_concurrently=True)

        op.create_index(
            "idx_jobs_active_sync",
            "jobs",
            ["last_seen"],
            unique=False,
            postgresql_concurrently=True,
            postgresql_where=sa.text(_ACTIVE_PREDICATE),
        )
        op.create_index(
            "idx_jobs_inactive_sync",
            "jobs",
            ["last_seen"],
            unique=False,
            postgresql_concurrently=True,
            postgresql_where=sa.text(_INACTIVE_PREDICATE),
        )


def downgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.drop_index("idx_jobs_active_sync", postgresql_concurrently=True)
        op.drop_index("idx_jobs_inactive_sync", postgresql_concurrently=True)

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
