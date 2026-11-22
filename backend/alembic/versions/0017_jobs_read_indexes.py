"""Indexes for the public job listing and related-jobs retrieval.

Production measurement (55 days) showed the public reads were dominated by
full-window scans of ``jobs``:

* ``get_related_candidates`` scanned every active job inside the 120-day
  posting window (471,551 rows) per job-detail view: ~285 TB of logical reads
  across ~1M calls.
* The company-filtered listing count and list both scanned the same window to
  find a few dozen rows, because no index covered ``company``.
* The default listing count heap-fetched every candidate row just to check
  ``is_active``.

These partial indexes let each query stop after the rows it needs. They are
narrow (~30-40 MB each) and only cover active rows, so the write cost added to
the pipeline is small compared with the read amplification they remove.

``CREATE INDEX CONCURRENTLY`` keeps the build online; it requires running
outside a transaction, hence the ``autocommit_block`` calls.

Revision ID: 0017_jobs_read_indexes
Revises: 0016_jobs_last_seen_index
Create Date: 2026-10-19 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0017_jobs_read_indexes"
down_revision: str | None = "0016_jobs_last_seen_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACTIVE_PREDICATE = "is_active IS TRUE"


def upgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        # Same-company related jobs and the company-filtered listing. The
        # count query can be index-only; the list fetches only the matching
        # rows' heap pages.
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_company_posted_id "
            f"ON jobs (company, posted_at DESC, id) WHERE {_ACTIVE_PREDICATE}"
        )
        # Same-category related jobs and the category-filtered listing.
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_category_posted_id "
            f"ON jobs (job_category, posted_at DESC, id) WHERE {_ACTIVE_PREDICATE}"
        )
        # Default listing count: index-only scan over just the active rows,
        # ordered for the paginated list.
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_active_posted_id "
            f"ON jobs (posted_at DESC, id) WHERE {_ACTIVE_PREDICATE}"
        )


def downgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_active_posted_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_category_posted_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_company_posted_id")
