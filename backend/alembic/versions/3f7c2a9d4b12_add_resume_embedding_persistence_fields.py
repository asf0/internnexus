"""add resume embedding persistence fields

Revision ID: 3f7c2a9d4b12
Revises: d4f5a9c7b321
Create Date: 2026-02-24 16:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = "3f7c2a9d4b12"
down_revision = "d4f5a9c7b321"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_resumes", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.add_column("user_resumes", sa.Column("encrypted_resume_text", sa.Text(), nullable=True))
    op.add_column("user_resumes", sa.Column("resume_embedding", Vector(dim=1024), nullable=True))
    op.add_column(
        "user_resumes", sa.Column("embedding_model", sa.String(length=120), nullable=True)
    )
    op.add_column("user_resumes", sa.Column("embedding_dim", sa.Integer(), nullable=True))
    op.add_column(
        "user_resumes", sa.Column("last_embedded_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("user_resumes", sa.Column("embedding_error", sa.Text(), nullable=True))
    op.create_index(
        op.f("ix_user_resumes_content_hash"), "user_resumes", ["content_hash"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_resumes_content_hash"), table_name="user_resumes")
    op.drop_column("user_resumes", "embedding_error")
    op.drop_column("user_resumes", "last_embedded_at")
    op.drop_column("user_resumes", "embedding_dim")
    op.drop_column("user_resumes", "embedding_model")
    op.drop_column("user_resumes", "resume_embedding")
    op.drop_column("user_resumes", "encrypted_resume_text")
    op.drop_column("user_resumes", "content_hash")
