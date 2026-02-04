"""fix job_category enum values

Revision ID: 20260203_000004
Revises: 20260203_000003
Create Date: 2026-02-03 13:00:00.000000

"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260203_000004"
down_revision = "20260203_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL doesn't allow modifying enums, so we need to recreate the type
    # First, rename the old enum
    op.execute("ALTER TYPE job_category RENAME TO job_category_old")
    
    # Create the new enum with correct values
    op.execute("""
    CREATE TYPE job_category AS ENUM (
        'software_engineering',
        'product_management',
        'data_science_ai',
        'quantitative_finance',
        'hardware_engineering'
    )
    """)
    
    # Convert data using a mapping function and temp column
    op.execute("""
    ALTER TABLE jobs 
    ADD COLUMN job_category_new job_category
    """)
    
    # Map old values to new values
    op.execute("""
    UPDATE jobs 
    SET job_category_new = CASE 
        WHEN job_category::text = 'Software Engineering' THEN 'software_engineering'::job_category
        WHEN job_category::text = 'Product Management' THEN 'product_management'::job_category
        WHEN job_category::text = 'Data Science, AI & Machine Learning' THEN 'data_science_ai'::job_category
        WHEN job_category::text = 'Quantitative Finance' THEN 'quantitative_finance'::job_category
        WHEN job_category::text = 'Hardware Engineering' THEN 'hardware_engineering'::job_category
        ELSE NULL
    END
    """)
    
    # Drop old column and rename new one
    op.execute("ALTER TABLE jobs DROP COLUMN job_category")
    op.execute("ALTER TABLE jobs RENAME COLUMN job_category_new TO job_category")
    
    # Drop old enum type
    op.execute("DROP TYPE job_category_old")


def downgrade() -> None:
    # Revert to old enum (not recommended)
    op.execute("ALTER TYPE job_category RENAME TO job_category_new")
    
    op.execute("""
    CREATE TYPE job_category AS ENUM (
        'Software Engineering',
        'Product Management',
        'Data Science, AI & Machine Learning',
        'Quantitative Finance',
        'Hardware Engineering'
    )
    """)
    
    op.execute("""
    ALTER TABLE jobs 
    ADD COLUMN job_category_old job_category
    """)
    
    op.execute("""
    UPDATE jobs 
    SET job_category_old = CASE 
        WHEN job_category::text = 'software_engineering' THEN 'Software Engineering'::job_category
        WHEN job_category::text = 'product_management' THEN 'Product Management'::job_category
        WHEN job_category::text = 'data_science_ai' THEN 'Data Science, AI & Machine Learning'::job_category
        WHEN job_category::text = 'quantitative_finance' THEN 'Quantitative Finance'::job_category
        WHEN job_category::text = 'hardware_engineering' THEN 'Hardware Engineering'::job_category
        ELSE NULL
    END
    """)
    
    op.execute("ALTER TABLE jobs DROP COLUMN job_category")
    op.execute("ALTER TABLE jobs RENAME COLUMN job_category_old TO job_category")
    
    op.execute("DROP TYPE job_category_new")
