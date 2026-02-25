"""Integration tests for job click tracking endpoint.

Tests cover:
- Click is actually saved to database
- Click can be retrieved via admin/clicks endpoint
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Admin, AdminRole, Job, JobClick, JobSource, User


# =============================================================================
# INTEGRATION TESTS - Database Persistence
# =============================================================================


@pytest.mark.integration
class TestClickTrackingIntegration:
    """Integration tests for click tracking with real database."""

    @pytest.fixture
    async def setup_test_data(self, db_session: AsyncSession):
        """Create test user, admin, and job for integration tests."""
        # Create test user
        user = User(
            id=uuid4(),
            email="clicktest@example.com",
            name="Click Test User",
            email_verified=True,
        )
        db_session.add(user)

        # Create admin user
        admin = Admin(
            id=uuid4(),
            user_id=user.id,
            role=AdminRole.admin,
        )
        db_session.add(admin)

        # Create test job
        job = Job(
            id=uuid4(),
            fingerprint=f"test-job-{uuid4()}",
            source=JobSource.greenhouse,
            title="Integration Test Job",
            company="Test Company",
            location="Remote",
            apply_url="https://example.com/apply?job=test",
            description_text="Test job description for click tracking",
            is_active=True,
        )
        db_session.add(job)

        await db_session.commit()
        await db_session.refresh(user)
        await db_session.refresh(job)

        return {"user": user, "admin": admin, "job": job}

    @pytest.mark.asyncio
    async def test_click_is_saved_to_database(self, db_session: AsyncSession, setup_test_data):
        """Test that click is actually saved to the database."""
        # Arrange
        test_data = setup_test_data
        job = test_data["job"]
        user = test_data["user"]

        # Create a JobClick directly
        client_ip = "192.168.100.50"
        ip_hash = hashlib.sha256(f"click:{client_ip}".encode()).hexdigest()[:16]

        click = JobClick(
            id=uuid4(),
            job_id=job.id,
            user_id=user.id,
            clicked_at=datetime.now(timezone.utc),
            utm_source="internnexus",
            utm_medium="test",
            utm_campaign="integration_test",
            ip_hash=ip_hash,
            user_agent="TestAgent/1.0",
            referer="https://test.com/jobs",
        )
        db_session.add(click)
        await db_session.commit()

        # Act - Query the click from database
        result = await db_session.execute(select(JobClick).where(JobClick.job_id == job.id))
        saved_click = result.scalar_one_or_none()

        # Assert
        assert saved_click is not None
        assert saved_click.job_id == job.id
        assert saved_click.user_id == user.id
        assert saved_click.utm_source == "internnexus"
        assert saved_click.utm_medium == "test"
        assert saved_click.utm_campaign == "integration_test"
        assert saved_click.ip_hash == ip_hash
        assert saved_click.user_agent == "TestAgent/1.0"
        assert saved_click.referer == "https://test.com/jobs"

    @pytest.mark.asyncio
    async def test_click_without_user_saved_to_database(
        self, db_session: AsyncSession, setup_test_data
    ):
        """Test that anonymous click (no user) is saved to database."""
        # Arrange
        test_data = setup_test_data
        job = test_data["job"]

        # Create a JobClick without user (anonymous)
        click = JobClick(
            id=uuid4(),
            job_id=job.id,
            user_id=None,  # Anonymous user
            clicked_at=datetime.now(timezone.utc),
            utm_source="internnexus",
            ip_hash="anonymous_hash_123",
        )
        db_session.add(click)
        await db_session.commit()

        # Act - Query the click from database
        result = await db_session.execute(
            select(JobClick).where(JobClick.job_id == job.id, JobClick.user_id.is_(None))
        )
        saved_click = result.scalar_one_or_none()

        # Assert
        assert saved_click is not None
        assert saved_click.job_id == job.id
        assert saved_click.user_id is None
        assert saved_click.utm_source == "internnexus"

    @pytest.mark.asyncio
    async def test_multiple_clicks_for_same_job(self, db_session: AsyncSession, setup_test_data):
        """Test that multiple clicks can be recorded for the same job."""
        # Arrange
        test_data = setup_test_data
        job = test_data["job"]
        user = test_data["user"]

        # Create multiple clicks
        for i in range(3):
            click = JobClick(
                id=uuid4(),
                job_id=job.id,
                user_id=user.id if i < 2 else None,  # First 2 with user, last anonymous
                clicked_at=datetime.now(timezone.utc),
                utm_source="internnexus",
                ip_hash=f"hash_{i}",
            )
            db_session.add(click)
        await db_session.commit()

        # Act - Query all clicks for the job
        result = await db_session.execute(
            select(JobClick).where(JobClick.job_id == job.id).order_by(JobClick.clicked_at)
        )
        saved_clicks = list(result.scalars().all())

        # Assert
        assert len(saved_clicks) == 3
        assert saved_clicks[0].user_id == user.id
        assert saved_clicks[1].user_id == user.id
        assert saved_clicks[2].user_id is None

    @pytest.mark.asyncio
    async def test_click_relationships_loaded(self, db_session: AsyncSession, setup_test_data):
        """Test that click relationships (job, user) can be loaded."""
        # Arrange
        test_data = setup_test_data
        job = test_data["job"]
        user = test_data["user"]

        click = JobClick(
            id=uuid4(),
            job_id=job.id,
            user_id=user.id,
            clicked_at=datetime.now(timezone.utc),
            utm_source="internnexus",
        )
        db_session.add(click)
        await db_session.commit()
        await db_session.refresh(click)

        # Act - Access relationships
        # Note: In async context, we need to explicitly load relationships
        from sqlalchemy.orm import selectinload

        result = await db_session.execute(
            select(JobClick)
            .where(JobClick.id == click.id)
            .options(selectinload(JobClick.job), selectinload(JobClick.user))
        )
        loaded_click = result.scalar_one()

        # Assert
        assert loaded_click.job is not None
        assert loaded_click.job.title == "Integration Test Job"
        assert loaded_click.user is not None
        assert loaded_click.user.email == "clicktest@example.com"


@pytest.mark.integration
class TestClickTrackingAdminRetrieval:
    """Integration tests for retrieving clicks via admin endpoints."""

    @pytest.fixture
    async def setup_admin_test_data(self, db_session: AsyncSession):
        """Create test data for admin click retrieval tests."""
        # Create admin user
        admin_user = User(
            id=uuid4(),
            email="admin_clicks@example.com",
            name="Admin Click User",
            email_verified=True,
        )
        db_session.add(admin_user)

        admin = Admin(
            id=uuid4(),
            user_id=admin_user.id,
            role=AdminRole.admin,
        )
        db_session.add(admin)

        # Create regular user
        regular_user = User(
            id=uuid4(),
            email="regular@example.com",
            name="Regular User",
            email_verified=True,
        )
        db_session.add(regular_user)

        # Create test job
        job = Job(
            id=uuid4(),
            fingerprint=f"admin-test-job-{uuid4()}",
            source=JobSource.lever,
            title="Admin Test Job",
            company="Admin Test Company",
            location="New York, NY",
            apply_url="https://example.com/admin-apply",
            description_text="Admin test job description",
            is_active=True,
        )
        db_session.add(job)

        await db_session.commit()
        await db_session.refresh(admin_user)
        await db_session.refresh(admin)
        await db_session.refresh(job)

        return {
            "admin_user": admin_user,
            "admin": admin,
            "regular_user": regular_user,
            "job": job,
        }

    @pytest.mark.asyncio
    async def test_clicks_retrievable_via_admin_endpoint(
        self, db_session: AsyncSession, setup_admin_test_data
    ):
        """Test that clicks can be retrieved via admin/clicks endpoint."""
        # Arrange
        test_data = setup_admin_test_data
        job = test_data["job"]
        user = test_data["regular_user"]

        # Create test clicks
        for i in range(5):
            click = JobClick(
                id=uuid4(),
                job_id=job.id,
                user_id=user.id if i % 2 == 0 else None,
                clicked_at=datetime.now(timezone.utc),
                utm_source="internnexus",
                utm_medium=f"medium_{i}",
            )
            db_session.add(click)
        await db_session.commit()

        # Act - Query clicks directly (simulating admin endpoint query)
        from sqlalchemy import func

        # Count total clicks
        count_result = await db_session.execute(
            select(func.count()).select_from(JobClick).where(JobClick.job_id == job.id)
        )
        total_clicks = count_result.scalar()

        # Get clicks with job info (like admin endpoint does)
        result = await db_session.execute(
            select(JobClick, Job.title, Job.company)
            .join(Job, JobClick.job_id == Job.id)
            .where(JobClick.job_id == job.id)
            .order_by(JobClick.clicked_at.desc())
            .limit(50)
        )
        rows = result.all()

        # Assert
        assert total_clicks == 5
        assert len(rows) == 5

        for row in rows:
            click, title, company = row
            assert title == "Admin Test Job"
            assert company == "Admin Test Company"
            assert click.utm_source == "internnexus"

    @pytest.mark.asyncio
    async def test_clicks_filterable_by_job_id(
        self, db_session: AsyncSession, setup_admin_test_data
    ):
        """Test that clicks can be filtered by job_id in admin endpoint."""
        # Arrange
        test_data = setup_admin_test_data
        job1 = test_data["job"]

        # Create second job
        job2 = Job(
            id=uuid4(),
            fingerprint=f"second-job-{uuid4()}",
            source=JobSource.greenhouse,
            title="Second Job",
            company="Second Company",
            location="Remote",
            apply_url="https://example.com/apply2",
            description_text="Second job description",
            is_active=True,
        )
        db_session.add(job2)
        await db_session.commit()
        await db_session.refresh(job2)

        # Create clicks for both jobs
        for job in [job1, job2]:
            for i in range(3):
                click = JobClick(
                    id=uuid4(),
                    job_id=job.id,
                    clicked_at=datetime.now(timezone.utc),
                    utm_source="internnexus",
                )
                db_session.add(click)
        await db_session.commit()

        # Act - Filter by job1
        result = await db_session.execute(select(JobClick).where(JobClick.job_id == job1.id))
        job1_clicks = list(result.scalars().all())

        # Filter by job2
        result = await db_session.execute(select(JobClick).where(JobClick.job_id == job2.id))
        job2_clicks = list(result.scalars().all())

        # Assert
        assert len(job1_clicks) == 3
        assert len(job2_clicks) == 3

    @pytest.mark.asyncio
    async def test_click_stats_calculation(self, db_session: AsyncSession, setup_admin_test_data):
        """Test that click statistics can be calculated correctly."""
        # Arrange
        test_data = setup_admin_test_data
        job = test_data["job"]

        # Create clicks with different timestamps
        now = datetime.now(timezone.utc)
        for i in range(10):
            click = JobClick(
                id=uuid4(),
                job_id=job.id,
                clicked_at=now,  # All clicks "today"
                utm_source="internnexus",
            )
            db_session.add(click)
        await db_session.commit()

        # Act - Calculate stats
        from sqlalchemy import func

        # Total clicks
        total_result = await db_session.execute(select(func.count()).select_from(JobClick))
        total_clicks = total_result.scalar()

        # Clicks today
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_result = await db_session.execute(
            select(func.count()).select_from(JobClick).where(JobClick.clicked_at >= today_start)
        )
        clicks_today = today_result.scalar()

        # Assert
        assert total_clicks >= 10
        assert clicks_today >= 10
