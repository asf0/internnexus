"""add city, state, country columns

Revision ID: 20260203_000003
Revises: 20260203_000002
Create Date: 2026-02-03 12:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260203_000003"
down_revision = "20260203_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("city", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("state", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("country", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "country")
    op.drop_column("jobs", "state")
    op.drop_column("jobs", "city")
