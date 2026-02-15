"""Add job_type and work_mode columns

Revision ID: 20260215_add_job_type_work_mode
Revises: 0273b3240827
Create Date: 2026-02-15

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260215_add_job_type_work_mode"
down_revision = "0273b3240827"
branch_labels = None
depends_on = None


def upgrade() -> None:
    job_type_enum = postgresql.ENUM(
        "internship", "full_time", "part_time", name="job_type", create_type=False
    )
    work_mode_enum = postgresql.ENUM(
        "remote", "hybrid", "on_site", name="work_mode", create_type=False
    )

    op.execute("CREATE TYPE job_type AS ENUM ('internship', 'full_time', 'part_time')")
    op.execute("CREATE TYPE work_mode AS ENUM ('remote', 'hybrid', 'on_site')")

    op.add_column("jobs", sa.Column("job_type", job_type_enum, nullable=True))
    op.add_column("jobs", sa.Column("work_mode", work_mode_enum, nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "work_mode")
    op.drop_column("jobs", "job_type")

    op.execute("DROP TYPE IF EXISTS work_mode")
    op.execute("DROP TYPE IF EXISTS job_type")
