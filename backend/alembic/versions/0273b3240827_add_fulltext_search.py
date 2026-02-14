"""add_fulltext_search

Revision ID: 0273b3240827
Revises: 20260213_add_pipeline_runs
Create Date: 2026-02-14 08:45:03.716142

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0273b3240827"
down_revision = "20260213_add_pipeline_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tsvector column for full-text search
    op.execute("""
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS search_vector tsvector
    """)

    # Create GIN index for fast full-text search
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_search_vector ON jobs USING GIN (search_vector)
    """)

    # Create trigger function to update search_vector
    op.execute("""
        CREATE OR REPLACE FUNCTION jobs_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.company, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.location, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.description_text, '')), 'D');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql
    """)

    # Create trigger
    op.execute("""
        DROP TRIGGER IF EXISTS jobs_search_vector_trigger ON jobs
    """)
    op.execute("""
        CREATE TRIGGER jobs_search_vector_trigger
            BEFORE INSERT OR UPDATE ON jobs
            FOR EACH ROW EXECUTE FUNCTION jobs_search_vector_update()
    """)

    # Populate existing rows
    op.execute("""
        UPDATE jobs SET search_vector =
            setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(company, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(location, '')), 'C') ||
            setweight(to_tsvector('english', COALESCE(description_text, '')), 'D')
        WHERE search_vector IS NULL
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS jobs_search_vector_trigger ON jobs")
    op.execute("DROP FUNCTION IF EXISTS jobs_search_vector_update()")
    op.execute("DROP INDEX IF EXISTS idx_jobs_search_vector")
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS search_vector")
