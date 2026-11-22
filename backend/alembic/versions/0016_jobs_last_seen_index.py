"""jobs last_seen index for scoped location normalization

The location normalization UPDATEs in pipeline/stages/cleanup/normalizer.py are
scoped to `last_seen >= since` (see cleanup_locations in batch_updater.py), but
no index has covered `last_seen` since 0007 replaced the last_seen sync indexes
with id-ordered ones. The scoping was therefore semantically correct but could
not avoid a sequential scan, leaving statements like

    UPDATE jobs SET city = NULL WHERE lower(city) IN (...)

averaging 4.5 s per call and reading ~6M blocks.

`last_seen` is highly selective for a per-run scope (552 of 352,144 rows in the
last day, 50,214 in the last week), so a plain btree makes the existing scoping
effective.

CREATE INDEX CONCURRENTLY is used to avoid blocking writes during index
construction. This requires running outside a transaction, hence the
autocommit_block() calls.

Revision ID: 0016_jobs_last_seen_index
Revises: 0015_authoritative_sessions
Create Date: 2026-07-26 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0016_jobs_last_seen_index"
down_revision: str | None = "0015_authoritative_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.create_index(
            "idx_jobs_last_seen",
            "jobs",
            ["last_seen"],
            unique=False,
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.drop_index("idx_jobs_last_seen", postgresql_concurrently=True)
