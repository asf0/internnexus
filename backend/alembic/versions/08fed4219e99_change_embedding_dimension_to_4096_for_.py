"""change embedding dimension to 4096 for qwen3

Revision ID: 08fed4219e99
Revises: 09732fefc9e6
Create Date: 2026-02-09 21:52:08.836366

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "08fed4219e99"
down_revision = "09732fefc9e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old column and recreate with 4096 dimensions for qwen3-embedding
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS description_embedding")
    op.execute("ALTER TABLE jobs ADD COLUMN description_embedding vector(4096)")


def downgrade() -> None:
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS description_embedding")
    op.execute("ALTER TABLE jobs ADD COLUMN description_embedding vector(768)")
