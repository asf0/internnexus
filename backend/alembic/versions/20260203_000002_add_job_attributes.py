"""Add job attributes and category fields.

Revision ID: 20260203_000002
Revises: 20260203_000001
Create Date: 2026-02-03 00:00:02.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260203_000002'
down_revision = '20260203_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    job_category_enum = postgresql.ENUM('Software Engineering', 'Product Management', 'Data Science, AI & Machine Learning', 'Quantitative Finance', 'Hardware Engineering', name='job_category')
    job_category_enum.create(op.get_bind())
    
    # Add columns to jobs table
    op.add_column('jobs', sa.Column('job_category', postgresql.ENUM('Software Engineering', 'Product Management', 'Data Science, AI & Machine Learning', 'Quantitative Finance', 'Hardware Engineering', name='job_category'), nullable=True))
    op.add_column('jobs', sa.Column('requires_sponsorship', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('jobs', sa.Column('requires_us_citizenship', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('jobs', sa.Column('application_closed', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('jobs', sa.Column('is_faang_plus', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('jobs', sa.Column('requires_advanced_degree', sa.Boolean(), server_default='false', nullable=True))


def downgrade() -> None:
    # Remove columns from jobs table
    op.drop_column('jobs', 'requires_advanced_degree')
    op.drop_column('jobs', 'is_faang_plus')
    op.drop_column('jobs', 'application_closed')
    op.drop_column('jobs', 'requires_us_citizenship')
    op.drop_column('jobs', 'requires_sponsorship')
    op.drop_column('jobs', 'job_category')
    
    # Drop enum type
    job_category_enum = postgresql.ENUM('Software Engineering', 'Product Management', 'Data Science, AI & Machine Learning', 'Quantitative Finance', 'Hardware Engineering', name='job_category')
    job_category_enum.drop(op.get_bind())
