"""change embedding dimensions to 1024

Revision ID: 7016200eb04f
Revises: ad80df2d2115
Create Date: 2026-02-10 22:14:52.799340

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = '7016200eb04f'
down_revision = 'ad80df2d2115'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop current 1536 column and add 1024
    op.drop_column("jobs", "description_embedding")
    op.add_column(
        "jobs",
        sa.Column("description_embedding", Vector(1024), nullable=True),
    )

def downgrade() -> None:
    # Revert back to 1536
    op.drop_column("jobs", "description_embedding")
    op.add_column(
        "jobs",
        sa.Column("description_embedding", Vector(1536), nullable=True),
    )