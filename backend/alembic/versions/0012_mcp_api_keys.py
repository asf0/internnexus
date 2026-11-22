"""Add user-scoped MCP API keys.

Revision ID: 0012_mcp_api_keys
Revises: 0011_job_board_snapshots
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0012_mcp_api_keys"
down_revision: str | None = "0011_job_board_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mcp_api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("key_prefix", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mcp_api_keys_key_hash", "mcp_api_keys", ["key_hash"], unique=True)
    op.create_index("ix_mcp_api_keys_user_id", "mcp_api_keys", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_mcp_api_keys_user_id", table_name="mcp_api_keys")
    op.drop_index("ix_mcp_api_keys_key_hash", table_name="mcp_api_keys")
    op.drop_table("mcp_api_keys")
