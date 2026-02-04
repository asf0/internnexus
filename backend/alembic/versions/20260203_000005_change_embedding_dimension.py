"""Change embedding dimension to 768 for nomic-embed-text

Revision ID: 20260203_000005
Revises: 20260203_000004
Create Date: 2026-02-03

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260203_000005"
down_revision = "20260203_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old column and recreate with new dimension
    # Since no embeddings are stored yet, this is safe
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS description_embedding")
    op.execute("ALTER TABLE jobs ADD COLUMN description_embedding vector(768)")


def downgrade() -> None:
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS description_embedding")
    op.execute("ALTER TABLE jobs ADD COLUMN description_embedding vector(1536)")
