"""Replace legacy last_seen synchronization indexes with ID-ordered indexes.

Revision ID: 0007_jobs_id_sync_contract
Revises: 0006_pg_stat_statements
Create Date: 2026-06-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_jobs_id_sync_contract"
down_revision: str | None = "0006_pg_stat_statements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACTIVE_PREDICATE = "is_active IS TRUE AND source <> 'manual'::job_source"
_INACTIVE_PREDICATE = "is_active IS FALSE AND source <> 'manual'::job_source"


def upgrade() -> None:
    """Drop legacy indexes concurrently and promote the ID-ordered indexes."""
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.drop_index("idx_jobs_active_sync", postgresql_concurrently=True)
        op.drop_index("idx_jobs_inactive_sync", postgresql_concurrently=True)
        op.execute("ALTER INDEX idx_jobs_active_id_sync RENAME TO idx_jobs_active_sync")
        op.execute("ALTER INDEX idx_jobs_inactive_id_sync RENAME TO idx_jobs_inactive_sync")


def downgrade() -> None:
    """Restore both additive ID indexes and the legacy last_seen indexes."""
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute("ALTER INDEX idx_jobs_active_sync RENAME TO idx_jobs_active_id_sync")
        op.execute("ALTER INDEX idx_jobs_inactive_sync RENAME TO idx_jobs_inactive_id_sync")
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
