"""add_search_vector_trigger

Revision ID: fa470ef03d54
Revises: c59f7c1eb6b3
Create Date: 2026-02-17 14:49:22.955744

"""

from alembic import op
import sqlalchemy as sa


revision = "fa470ef03d54"
down_revision = "c59f7c1eb6b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION get_country_search_terms(country_name TEXT) 
        RETURNS TEXT AS $$
        BEGIN
            RETURN CASE 
                WHEN country_name = 'United States' THEN 'USA US United States America'
                WHEN country_name = 'United Kingdom' THEN 'UK United Kingdom Britain England'
                WHEN country_name = 'South Korea' THEN 'Korea South Korea KR'
                WHEN country_name = 'Japan' THEN 'Japan JP'
                WHEN country_name = 'China' THEN 'China CN Chinese'
                WHEN country_name = 'Brazil' THEN 'Brazil BR'
                WHEN country_name = 'Canada' THEN 'Canada CA'
                WHEN country_name = 'Australia' THEN 'Australia AU'
                WHEN country_name = 'Germany' THEN 'Germany DE'
                WHEN country_name = 'France' THEN 'France FR'
                WHEN country_name = 'India' THEN 'India IN'
                WHEN country_name = 'Singapore' THEN 'Singapore SG'
                WHEN country_name = 'Netherlands' THEN 'Netherlands NL Holland'
                WHEN country_name = 'Switzerland' THEN 'Switzerland CH'
                WHEN country_name = 'Spain' THEN 'Spain ES'
                WHEN country_name = 'Italy' THEN 'Italy IT'
                WHEN country_name = 'Mexico' THEN 'Mexico MX'
                WHEN country_name = 'Argentina' THEN 'Argentina AR'
                WHEN country_name = 'Chile' THEN 'Chile CL'
                WHEN country_name = 'Colombia' THEN 'Colombia CO'
                WHEN country_name = 'Poland' THEN 'Poland PL'
                WHEN country_name = 'Sweden' THEN 'Sweden SE'
                WHEN country_name = 'Norway' THEN 'Norway NO'
                WHEN country_name = 'Denmark' THEN 'Denmark DK'
                WHEN country_name = 'Finland' THEN 'Finland FI'
                WHEN country_name = 'Ireland' THEN 'Ireland IE'
                WHEN country_name = 'New Zealand' THEN 'New Zealand NZ'
                WHEN country_name = 'Taiwan' THEN 'Taiwan TW'
                WHEN country_name = 'Hong Kong' THEN 'Hong Kong HK'
                WHEN country_name = 'Vietnam' THEN 'Vietnam VN'
                WHEN country_name = 'Thailand' THEN 'Thailand TH'
                WHEN country_name = 'Malaysia' THEN 'Malaysia MY'
                WHEN country_name = 'Indonesia' THEN 'Indonesia ID'
                WHEN country_name = 'Philippines' THEN 'Philippines PH'
                WHEN country_name = 'South Africa' THEN 'South Africa ZA'
                WHEN country_name = 'United Arab Emirates' THEN 'UAE United Arab Emirates'
                WHEN country_name = 'Israel' THEN 'Israel IL'
                WHEN country_name = 'Turkey' THEN 'Turkey TR'
                WHEN country_name = 'Russia' THEN 'Russia RU'
                ELSE COALESCE(country_name, '')
            END;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION get_region_from_country(country_name TEXT) 
        RETURNS TEXT AS $$
        BEGIN
            RETURN CASE 
                WHEN country_name IN ('Japan', 'South Korea', 'China', 'Singapore', 
                    'Hong Kong', 'Taiwan', 'India', 'Malaysia', 'Thailand', 'Vietnam',
                    'Philippines', 'Indonesia', 'Australia', 'New Zealand')
                THEN 'APAC Asia-Pacific AsiaPacific'
                WHEN country_name IN ('United Kingdom', 'Germany', 'France', 'Netherlands',
                    'Belgium', 'Switzerland', 'Austria', 'Spain', 'Italy', 'Portugal',
                    'Poland', 'Sweden', 'Norway', 'Denmark', 'Finland', 'Ireland',
                    'South Africa', 'United Arab Emirates', 'Israel', 'Turkey', 'Russia')
                THEN 'EMEA Europe Middle East Africa'
                WHEN country_name IN ('Brazil', 'Argentina', 'Chile', 'Colombia', 'Peru',
                    'Mexico', 'Ecuador', 'Uruguay', 'Paraguay', 'Bolivia', 'Venezuela')
                THEN 'LATAM Latin America'
                WHEN country_name IN ('United States', 'Canada')
                THEN 'NA North America'
                ELSE ''
            END;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION update_job_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector := 
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.company, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.location, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.city, '')), 'C') ||
                setweight(to_tsvector('english', get_country_search_terms(NEW.country)), 'C') ||
                setweight(to_tsvector('english', get_region_from_country(NEW.country)), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.description_text, '')), 'D');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER job_search_vector_trigger
            BEFORE INSERT OR UPDATE ON jobs
            FOR EACH ROW EXECUTE FUNCTION update_job_search_vector();
    """)

    op.execute("""
        UPDATE jobs SET search_vector = 
            setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(company, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(location, '')), 'C') ||
            setweight(to_tsvector('english', COALESCE(city, '')), 'C') ||
            setweight(to_tsvector('english', get_country_search_terms(country)), 'C') ||
            setweight(to_tsvector('english', get_region_from_country(country)), 'C') ||
            setweight(to_tsvector('english', COALESCE(description_text, '')), 'D')
        WHERE is_active = true;
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_search_vector ON jobs USING GIN(search_vector);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_jobs_search_vector;")
    op.execute("DROP TRIGGER IF EXISTS job_search_vector_trigger ON jobs;")
    op.execute("DROP FUNCTION IF EXISTS update_job_search_vector();")
    op.execute("DROP FUNCTION IF EXISTS get_region_from_country(TEXT);")
    op.execute("DROP FUNCTION IF EXISTS get_country_search_terms(TEXT);")
