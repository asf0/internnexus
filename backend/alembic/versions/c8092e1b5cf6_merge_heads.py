"""merge_heads

Revision ID: c8092e1b5cf6
Revises: 2d97fe7477ec, 20260212_password_invalidation
Create Date: 2026-02-12 18:02:24.060262

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c8092e1b5cf6'
down_revision = ('2d97fe7477ec', '20260212_password_invalidation')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
