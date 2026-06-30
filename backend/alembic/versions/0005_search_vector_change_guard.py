"""Recompute job search vectors only when their source fields change.

Revision ID: 0005_search_vector_change_guard
Revises: 0004_pipeline_job_sightings
Create Date: 2026-06-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005_search_vector_change_guard"
down_revision: str | None = "0004_pipeline_job_sightings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION update_job_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE'
       AND OLD.title IS NOT DISTINCT FROM NEW.title
       AND OLD.company IS NOT DISTINCT FROM NEW.company
       AND OLD.location IS NOT DISTINCT FROM NEW.location
       AND OLD.city IS NOT DISTINCT FROM NEW.city
       AND OLD.state IS NOT DISTINCT FROM NEW.state
       AND OLD.country IS NOT DISTINCT FROM NEW.country
       AND OLD.description_text IS NOT DISTINCT FROM NEW.description_text
    THEN
        RETURN NEW;
    END IF;

    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.company, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.location, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.city, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.state, '')), 'C') ||
        setweight(to_tsvector('english', get_country_search_terms(NEW.country)), 'C') ||
        setweight(to_tsvector('english', get_region_from_country(NEW.country)), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.description_text, '')), 'D');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

_OLD_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION update_job_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.company, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.location, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.city, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.state, '')), 'C') ||
        setweight(to_tsvector('english', get_country_search_terms(NEW.country)), 'C') ||
        setweight(to_tsvector('english', get_region_from_country(NEW.country)), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.description_text, '')), 'D');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def _create_trigger(columns: str) -> None:
    op.execute(
        f"""
        CREATE TRIGGER job_search_vector_trigger
        BEFORE INSERT OR UPDATE OF {columns} ON jobs
        FOR EACH ROW EXECUTE FUNCTION update_job_search_vector()
        """
    )


def upgrade() -> None:
    op.execute(_FUNCTION_SQL)
    op.execute("DROP TRIGGER IF EXISTS job_search_vector_trigger ON jobs")
    _create_trigger("title, company, location, city, state, country, description_text")


def downgrade() -> None:
    op.execute(_OLD_FUNCTION_SQL)
    op.execute("DROP TRIGGER IF EXISTS job_search_vector_trigger ON jobs")
    _create_trigger("title, company, location, description_text")
