"""Add performance indexes for search and filtering

Revision ID: 20260216_performance_indexes
Revises: 20260215_add_job_type_work_mode
Create Date: 2026-02-16

Indexes added:
- Trigram indexes for ILIKE text search (title, company, location)
- IVFFlat index for vector similarity search
- Composite indexes for common filter patterns

Note: Uses raw DBAPI cursor with autocommit for CONCURRENT index creation.
"""

from __future__ import annotations

from alembic import op


revision = "20260216_performance_indexes"
down_revision = "20260215_add_job_type_work_mode"
branch_labels = None
depends_on = None


INDEXES = [
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_title_trgm ON jobs USING gin (title gin_trgm_ops)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_company_trgm ON jobs USING gin (company gin_trgm_ops)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_location_trgm ON jobs USING gin (location gin_trgm_ops)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_embedding ON jobs USING ivfflat (description_embedding vector_cosine_ops) WITH (lists = 100) WHERE description_embedding IS NOT NULL",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_active_posted ON jobs (is_active, posted_at DESC) WHERE is_active = true",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_category_active ON jobs (job_category, is_active) WHERE is_active = true AND job_category IS NOT NULL",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_company_active ON jobs (company, is_active) WHERE is_active = true",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_source_active ON jobs (source, is_active) WHERE is_active = true",
]

DROP_INDEXES = [
    "DROP INDEX CONCURRENTLY IF EXISTS idx_job_source_active",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_job_company_active",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_job_category_active",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_job_active_posted",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_job_embedding",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_job_location_trgm",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_job_company_trgm",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_job_title_trgm",
]


def upgrade() -> None:
    connection = op.get_bind()
    dbapi_conn = connection.connection.connection
    old_isolation = dbapi_conn.isolation_level
    dbapi_conn.set_isolation_level(0)

    cursor = dbapi_conn.cursor()
    try:
        for sql in INDEXES:
            cursor.execute(sql)
    finally:
        cursor.close()
        dbapi_conn.set_isolation_level(old_isolation)


def downgrade() -> None:
    connection = op.get_bind()
    dbapi_conn = connection.connection.connection
    old_isolation = dbapi_conn.isolation_level
    dbapi_conn.set_isolation_level(0)

    cursor = dbapi_conn.cursor()
    try:
        for sql in DROP_INDEXES:
            cursor.execute(sql)
    finally:
        cursor.close()
        dbapi_conn.set_isolation_level(old_isolation)
