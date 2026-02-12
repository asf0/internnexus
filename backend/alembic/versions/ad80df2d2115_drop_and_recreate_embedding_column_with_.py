"""Drop and recreate embedding column with 1536 dimensions

Revision ID: ad80df2d2115
Revises: 4fe9e032b963
Create Date: 2026-02-10 22:05:26.199629

"""

from alembic import op
import sqlalchemy as sa

from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = "ad80df2d2115"
down_revision = "4fe9e032b963"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("jobs", "description_embedding")
    op.add_column(
        "jobs",
        sa.Column("description_embedding", Vector(1536), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("jobs", "description_embedding")
    op.add_column(
        "jobs",
        sa.Column("description_embedding", Vector(4096), nullable=True),
    )
