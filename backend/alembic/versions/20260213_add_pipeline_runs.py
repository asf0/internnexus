"""add pipeline_runs table

Revision ID: 20260213_add_pipeline_runs
Revises: c8092e1b5cf6
Create Date: 2026-02-13

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260213_add_pipeline_runs"
down_revision = "20260212_add_new_job_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'pipeline_run_status') THEN
                CREATE TYPE pipeline_run_status AS ENUM ('running', 'completed', 'failed');
            END IF;
        END
        $$
    """)

    op.create_table(
        "pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "running", "completed", "failed", name="pipeline_run_status", create_type=False
            ),
            nullable=False,
            server_default="running",
        ),
        sa.Column("step_completed", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_step", sa.String(), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("results", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("pipeline_runs")
    op.execute("DROP TYPE IF EXISTS pipeline_run_status")
