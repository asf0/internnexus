"""Make database sessions authoritative and clear retained OAuth credentials.

Revision ID: 0015_authoritative_sessions
Revises: 0014_embedding_input_hash
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0015_authoritative_sessions"
down_revision: str | None = "0014_embedding_input_hash"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    verification_count = connection.execute(
        sa.text("SELECT count(*) FROM verification_tokens")
    ).scalar_one()
    if verification_count:
        raise RuntimeError(
            "verification_tokens is not empty; complete the pre-deployment audit before retrying"
        )

    op.execute(
        "UPDATE accounts SET access_token = NULL, refresh_token = NULL, "
        "expires_at = NULL, token_type = NULL, scope = NULL, id_token = NULL, session_state = NULL"
    )
    op.drop_index("ix_sessions_token", table_name="sessions")
    op.alter_column(
        "sessions", "token", new_column_name="jti", existing_type=sa.String(), existing_nullable=False
    )
    op.create_index("ix_sessions_jti", "sessions", ["jti"], unique=True)
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"], unique=False)
    op.drop_index("ix_verification_tokens_token", table_name="verification_tokens")
    op.drop_table("verification_tokens")


def downgrade() -> None:
    op.create_table(
        "verification_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("identifier", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("identifier", "token", name="uix_identifier_token"),
    )
    op.create_index("ix_verification_tokens_token", "verification_tokens", ["token"], unique=True)
    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    op.drop_index("ix_sessions_jti", table_name="sessions")
    op.alter_column(
        "sessions", "jti", new_column_name="token", existing_type=sa.String(), existing_nullable=False
    )
    op.create_index("ix_sessions_token", "sessions", ["token"], unique=True)
