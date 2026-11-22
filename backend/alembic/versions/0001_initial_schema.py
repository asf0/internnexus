"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-25 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_search_helpers() -> None:
    op.execute(
        """
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
        """
    )
    op.execute(
        """
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
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_job_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.company, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.location, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.city, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.state, '')), 'C') ||
                setweight(to_tsvector('english', get_country_search_terms(NEW.country)), 'C') ||
                setweight(to_tsvector('english', get_region_from_country(NEW.country)), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.description_text, '')), 'D');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    job_source = sa.Enum('greenhouse', 'lever', 'ashby', 'manual', name='job_source')
    job_type = sa.Enum('internship', 'full_time', 'part_time', name='job_type')
    work_mode = sa.Enum('remote', 'hybrid', 'on_site', name='work_mode')
    admin_role = sa.Enum('admin', 'super_admin', name='admin_role')
    pipeline_run_status = sa.Enum('running', 'completed', 'failed', name='pipeline_run_status')
    pipeline_command_status = sa.Enum('pending', 'running', 'completed', 'failed', name='pipeline_command_status')

    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('fingerprint', sa.String(), nullable=False),
        sa.Column('source', job_source, nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('company', sa.String(), nullable=False),
        sa.Column('location', sa.String(), nullable=False),
        sa.Column('city', sa.String(), nullable=True),
        sa.Column('state', sa.String(), nullable=True),
        sa.Column('country', sa.String(), nullable=True),
        sa.Column('apply_url', sa.String(), nullable=False),
        sa.Column('description_text', sa.Text(), nullable=False),
        sa.Column('description_embedding', Vector(dim=2560), nullable=True),
        sa.Column('embedding_skip_reason', sa.String(length=50), nullable=True),
        sa.Column('embedding_skipped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.Column('job_category', sa.String(length=100), nullable=True),
        sa.Column('job_type', job_type, nullable=True),
        sa.Column('work_mode', work_mode, nullable=True),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_jobs_fingerprint', 'jobs', ['fingerprint'], unique=True)

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('image', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('hashed_password', sa.String(), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('job_title', sa.String(), nullable=True),
        sa.Column('company', sa.String(), nullable=True),
        sa.Column('industry', sa.String(), nullable=True),
        sa.Column('skills', sa.String(), nullable=True),
        sa.Column('linkedin_url', sa.String(), nullable=True),
        sa.Column('portfolio_url', sa.String(), nullable=True),
        sa.Column('preferred_locations', sa.String(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table(
        'pipeline_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('status', pipeline_run_status, nullable=False, server_default='running'),
        sa.Column('step_completed', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_step', sa.String(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('results', sa.Text(), nullable=True),
    )

    op.create_table(
        'accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('provider_account_id', sa.String(), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('token_type', sa.String(), nullable=True),
        sa.Column('scope', sa.String(), nullable=True),
        sa.Column('id_token', sa.Text(), nullable=True),
        sa.Column('session_state', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('provider', 'provider_account_id', name='uix_provider_account'),
    )

    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_sessions_token', 'sessions', ['token'], unique=True)

    op.create_table(
        'verification_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('identifier', sa.String(), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('identifier', 'token', name='uix_identifier_token'),
    )
    op.create_index('ix_verification_tokens_token', 'verification_tokens', ['token'], unique=True)

    op.create_table(
        'password_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'admins',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('role', admin_role, nullable=False, server_default='admin'),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('notes', sa.Text(), nullable=True),
    )

    op.create_table(
        'admin_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('actor_email', sa.String(length=255), nullable=True),
        sa.Column('action', sa.String(length=120), nullable=False),
        sa.Column('target_type', sa.String(length=80), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_admin_audit_logs_actor_user_id', 'admin_audit_logs', ['actor_user_id'], unique=False)
    op.create_index('ix_admin_audit_logs_action', 'admin_audit_logs', ['action'], unique=False)
    op.create_index('ix_admin_audit_logs_target_type', 'admin_audit_logs', ['target_type'], unique=False)
    op.create_index('ix_admin_audit_logs_target_id', 'admin_audit_logs', ['target_id'], unique=False)
    op.create_index('ix_admin_audit_logs_created_at', 'admin_audit_logs', ['created_at'], unique=False)

    op.create_table(
        'job_clicks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('clicked_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('utm_source', sa.String(length=50), nullable=False, server_default='internnexus'),
        sa.Column('utm_medium', sa.String(length=50), nullable=True),
        sa.Column('utm_campaign', sa.String(length=100), nullable=True),
        sa.Column('ip_hash', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('referer', sa.String(length=500), nullable=True),
    )
    op.create_index('ix_job_clicks_job_id', 'job_clicks', ['job_id'], unique=False)
    op.create_index('ix_job_clicks_clicked_at', 'job_clicks', ['clicked_at'], unique=False)

    op.create_table(
        'user_resumes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ready'),
        sa.Column('encrypted_resume_text', sa.Text(), nullable=True),
        sa.Column('resume_embedding', Vector(dim=2560), nullable=True),
        sa.Column('embedding_model', sa.String(length=120), nullable=True),
        sa.Column('embedding_dim', sa.Integer(), nullable=True),
        sa.Column('last_embedded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('embedding_error', sa.Text(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_user_resumes_file_hash', 'user_resumes', ['file_hash'], unique=False)
    op.create_index('ix_user_resumes_content_hash', 'user_resumes', ['content_hash'], unique=False)

    op.create_table(
        'saved_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'job_id', name='uix_saved_jobs_user_job'),
    )
    op.create_index('ix_saved_jobs_user_id', 'saved_jobs', ['user_id'], unique=False)
    op.create_index('ix_saved_jobs_job_id', 'saved_jobs', ['job_id'], unique=False)

    op.create_table(
        'applied_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'job_id', name='uix_applied_jobs_user_job'),
    )
    op.create_index('ix_applied_jobs_user_id', 'applied_jobs', ['user_id'], unique=False)
    op.create_index('ix_applied_jobs_job_id', 'applied_jobs', ['job_id'], unique=False)

    op.create_table(
        'user_notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(length=80), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'pipeline_commands',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('status', pipeline_command_status, nullable=False, server_default='pending'),
        sa.Column('step', sa.String(), nullable=True),
        sa.Column('skip_discover', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('dry_run', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('process_all', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('test_mode', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('limit', sa.Integer(), nullable=True),
        sa.Column('requested_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pipeline_runs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_pipeline_commands_status_created_at', 'pipeline_commands', ['status', 'created_at'], unique=False)

    _create_search_helpers()
    op.execute(
        """
        CREATE TRIGGER job_search_vector_trigger
            BEFORE INSERT OR UPDATE OF title, company, location, description_text ON jobs
            FOR EACH ROW EXECUTE FUNCTION update_job_search_vector();
        """
    )
    op.execute('CREATE INDEX IF NOT EXISTS idx_jobs_search_vector ON jobs USING GIN(search_vector)')


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS idx_jobs_search_vector')
    op.execute('DROP TRIGGER IF EXISTS job_search_vector_trigger ON jobs')
    op.execute('DROP FUNCTION IF EXISTS update_job_search_vector()')
    op.execute('DROP FUNCTION IF EXISTS get_region_from_country(TEXT)')
    op.execute('DROP FUNCTION IF EXISTS get_country_search_terms(TEXT)')

    op.drop_table('pipeline_commands')
    op.drop_table('user_notifications')
    op.drop_table('applied_jobs')
    op.drop_table('saved_jobs')
    op.drop_table('user_resumes')
    op.drop_table('job_clicks')
    op.drop_table('admin_audit_logs')
    op.drop_table('admins')
    op.drop_table('password_history')
    op.drop_table('verification_tokens')
    op.drop_table('sessions')
    op.drop_table('accounts')
    op.drop_table('pipeline_runs')
    op.drop_table('users')
    op.drop_table('jobs')

    for enum_name in (
        'pipeline_command_status',
        'pipeline_run_status',
        'admin_role',
        'work_mode',
        'job_type',
        'job_source',
    ):
        postgresql.ENUM(name=enum_name).drop(op.get_bind(), checkfirst=True)
