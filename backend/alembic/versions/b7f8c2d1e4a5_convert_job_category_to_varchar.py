"""convert_job_category_to_varchar

Revision ID: b7f8c2d1e4a5
Revises: a9470a9285c7
Create Date: 2026-02-21 12:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b7f8c2d1e4a5"
down_revision = "a9470a9285c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Convert job_category from ENUM to VARCHAR(100)."""
    # Step 1: Alter column type from enum to varchar, converting existing values
    # The USING clause converts enum values to their string representation
    op.execute("""
        ALTER TABLE jobs
        ALTER COLUMN job_category TYPE VARCHAR(100)
        USING job_category::text
    """)

    # Step 2: Drop the enum type (no longer needed)
    op.execute("DROP TYPE IF EXISTS job_category")


def downgrade() -> None:
    """Convert job_category back from VARCHAR to ENUM."""
    # Step 1: Create the enum type
    op.execute("""
        CREATE TYPE job_category AS ENUM (
            'software_engineering',
            'product_management',
            'data_science_ai',
            'quantitative_finance',
            'hardware_engineering'
        )
    """)

    # Step 2: Alter column type back to enum
    # Values that don't match the enum will become NULL
    op.execute("""
        ALTER TABLE jobs
        ALTER COLUMN job_category TYPE job_category
        USING CASE
            WHEN job_category IN ('software_engineering', 'product_management',
                                   'data_science_ai', 'quantitative_finance',
                                   'hardware_engineering')
            THEN job_category::job_category
            ELSE NULL
        END
    """)
