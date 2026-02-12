"""fix_embedding_dimensions_to_1024

Revision ID: 2d97fe7477ec
Revises: 7016200eb04f
Create Date: 2026-02-10 22:18:58.334332

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '2d97fe7477ec'
down_revision = '7016200eb04f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("jobs", "description_embedding")
    op.add_column("jobs", sa.Column("description_embedding", Vector(1024), nullable=True))

def downgrade() -> None:
    # Go from 1024 -> 1536
    op.drop_column("jobs", "description_embedding")
    op.add_column("jobs", sa.Column("description_embedding", Vector(1536), nullable=True))