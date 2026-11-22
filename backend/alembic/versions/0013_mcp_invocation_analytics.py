"""Add durable MCP invocation analytics.

Revision ID: 0013_mcp_invocation_analytics
Revises: 0012_mcp_api_keys
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0013_mcp_invocation_analytics"
down_revision: str | None = "0012_mcp_api_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mcp_invocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mcp_api_key_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tool_name", sa.String(length=80), nullable=False),
        sa.Column("invoked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("result_count", sa.Integer(), nullable=True),
        sa.Column("error_category", sa.String(length=80), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mcp_api_key_id"], ["mcp_api_keys.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mcp_invocations_user_id", "mcp_invocations", ["user_id"])
    op.create_index("ix_mcp_invocations_mcp_api_key_id", "mcp_invocations", ["mcp_api_key_id"])
    op.create_index("ix_mcp_invocations_tool_name", "mcp_invocations", ["tool_name"])
    op.create_index("ix_mcp_invocations_invoked_at", "mcp_invocations", ["invoked_at"])
    op.create_index("ix_mcp_invocations_success", "mcp_invocations", ["success"])
    op.create_index("ix_mcp_invocations_job_id", "mcp_invocations", ["job_id"])
    op.create_index("ix_mcp_invocations_tool_invoked_at", "mcp_invocations", ["tool_name", "invoked_at"])


def downgrade() -> None:
    op.drop_index("ix_mcp_invocations_tool_invoked_at", table_name="mcp_invocations")
    op.drop_index("ix_mcp_invocations_job_id", table_name="mcp_invocations")
    op.drop_index("ix_mcp_invocations_success", table_name="mcp_invocations")
    op.drop_index("ix_mcp_invocations_invoked_at", table_name="mcp_invocations")
    op.drop_index("ix_mcp_invocations_tool_name", table_name="mcp_invocations")
    op.drop_index("ix_mcp_invocations_mcp_api_key_id", table_name="mcp_invocations")
    op.drop_index("ix_mcp_invocations_user_id", table_name="mcp_invocations")
    op.drop_table("mcp_invocations")
