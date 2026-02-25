"""optimize_search_vector_trigger_for_pipeline_sync

Revision ID: 9d71b1e8a4c2
Revises: 6a2b4c8d9e10
Create Date: 2026-02-24 14:30:00.000000

"""

from alembic import op


revision = "9d71b1e8a4c2"
down_revision = "6a2b4c8d9e10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS job_search_vector_trigger ON jobs;")
    op.execute(
        """
        CREATE TRIGGER job_search_vector_trigger
            BEFORE INSERT OR UPDATE OF title, company, location, description_text ON jobs
            FOR EACH ROW EXECUTE FUNCTION update_job_search_vector();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS job_search_vector_trigger ON jobs;")
    op.execute(
        """
        CREATE TRIGGER job_search_vector_trigger
            BEFORE INSERT OR UPDATE ON jobs
            FOR EACH ROW EXECUTE FUNCTION update_job_search_vector();
        """
    )
