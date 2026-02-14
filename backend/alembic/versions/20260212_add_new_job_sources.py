"""Add workday, ashby, smartrecruiters to job_source enum

Revision ID: 20260212_add_new_job_sources
Revises: c8092e1b5cf6
Create Date: 2026-02-12

"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260212_add_new_job_sources"
down_revision: Union[str, None] = "c8092e1b5cf6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE job_source ADD VALUE IF NOT EXISTS 'workday'")
    op.execute("ALTER TYPE job_source ADD VALUE IF NOT EXISTS 'ashby'")
    op.execute("ALTER TYPE job_source ADD VALUE IF NOT EXISTS 'smartrecruiters'")


def downgrade() -> None:
    pass
