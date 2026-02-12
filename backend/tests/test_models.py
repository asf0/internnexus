"""Tests for database models."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from app.models import (
    Account,
    Job,
    JobCategory,
    JobSource,
    PasswordHistory,
    Session as UserSession,
    User,
    VerificationToken,
)


class TestUserModel:
    """Test User model."""

    def test_create_user(self, db_session: Session):
        """Test creating a user."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            name="Test User",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert isinstance(user.id, UUID)
        assert user.email == "test@example.com"
        assert user.created_at is not None

    def test_user_email_unique(self, db_session: Session, sample_user: User):
        """Test that user email must be unique."""
        duplicate_user = User(
            id=uuid4(),
            email=sample_user.email,  # Same email
            name="Another User",
        )
        db_session.add(duplicate_user)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_user_optional_fields(self, db_session: Session):
        """Test creating user with optional fields."""
        user = User(
            id=uuid4(),
            email="minimal@example.com",
        )
        db_session.add(user)
        db_session.commit()

        assert user.name is None
        assert user.hashed_password is None
        assert user.bio is None

    def test_user_accounts_relationship(self, db_session: Session, sample_user: User):
        """Test user accounts relationship."""
        account = Account(
            user_id=sample_user.id,
            provider="github",
            provider_account_id="123456",
        )
        db_session.add(account)
        db_session.commit()

        db_session.refresh(sample_user)
        assert len(sample_user.accounts) == 1
        assert sample_user.accounts[0].provider == "github"


class TestAccountModel:
    """Test Account model."""

    def test_create_account(self, db_session: Session, sample_user: User):
        """Test creating an account."""
        account = Account(
            user_id=sample_user.id,
            provider="google",
            provider_account_id="google_123",
            access_token="access_token",
            refresh_token="refresh_token",
        )
        db_session.add(account)
        db_session.commit()

        assert account.id is not None
        assert account.user_id == sample_user.id
        assert account.provider == "google"

    def test_account_user_relationship(self, db_session: Session, sample_user: User):
        """Test account user relationship."""
        account = Account(
            user_id=sample_user.id,
            provider="credentials",
            provider_account_id=sample_user.email,
        )
        db_session.add(account)
        db_session.commit()

        db_session.refresh(account)
        assert account.user is not None
        assert account.user.id == sample_user.id

    def test_account_unique_constraint(self, db_session: Session, sample_user: User):
        """Test account unique constraint on provider + provider_account_id."""
        account1 = Account(
            user_id=sample_user.id,
            provider="github",
            provider_account_id="same_id",
        )
        db_session.add(account1)
        db_session.commit()

        account2 = Account(
            user_id=sample_user.id,
            provider="github",
            provider_account_id="same_id",  # Same provider and ID
        )
        db_session.add(account2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestJobModel:
    """Test Job model."""

    def test_create_job(self, db_session: Session):
        """Test creating a job."""
        job = Job(
            id=uuid4(),
            fingerprint=f"test-{uuid4()}",
            source=JobSource.greenhouse,
            title="Software Engineer",
            company="Test Company",
            location="San Francisco, CA",
            apply_url="https://example.com/apply",
            description_text="Job description here",
        )
        db_session.add(job)
        db_session.commit()

        assert job.id is not None
        assert job.is_active is True  # Default value
        assert job.last_seen is not None

    def test_job_fingerprint_unique(self, db_session: Session, sample_job: Job):
        """Test that job fingerprint must be unique."""
        duplicate_job = Job(
            id=uuid4(),
            fingerprint=sample_job.fingerprint,  # Same fingerprint
            source=JobSource.greenhouse,
            title="Another Job",
            company="Another Company",
            location="NYC",
            apply_url="https://example.com",
            description_text="Description",
        )
        db_session.add(duplicate_job)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_job_categories(self, db_session: Session):
        """Test job categories enum."""
        job = Job(
            id=uuid4(),
            fingerprint=f"cat-test-{uuid4()}",
            source=JobSource.lever,
            title="Data Scientist",
            company="Data Co",
            location="Remote",
            apply_url="https://example.com",
            description_text="Data science job",
            job_category=JobCategory.data_science_ai,
        )
        db_session.add(job)
        db_session.commit()

        assert job.job_category == JobCategory.data_science_ai

    def test_job_boolean_flags(self, db_session: Session):
        """Test job boolean flags."""
        job = Job(
            id=uuid4(),
            fingerprint=f"flags-{uuid4()}",
            source=JobSource.greenhouse,
            title="FAANG Job",
            company="Google",
            location="Mountain View, CA",
            apply_url="https://google.com",
            description_text="FAANG job",
            visa_sponsored=True,
            f1_friendly=True,
            is_faang_plus=True,
            requires_us_citizenship=False,
        )
        db_session.add(job)
        db_session.commit()

        assert job.visa_sponsored is True
        assert job.f1_friendly is True
        assert job.is_faang_plus is True
        assert job.requires_us_citizenship is False


class TestSessionModel:
    """Test Session model."""

    def test_create_session(self, db_session: Session, sample_user: User):
        """Test creating a session."""
        session = UserSession(
            user_id=sample_user.id,
            token="session_token_123",
            expires_at=datetime.now(timezone.utc),
        )
        db_session.add(session)
        db_session.commit()

        assert session.id is not None
        assert session.user_id == sample_user.id

    def test_session_user_relationship(self, db_session: Session, sample_user: User):
        """Test session user relationship."""
        session = UserSession(
            user_id=sample_user.id,
            token="token_456",
            expires_at=datetime.now(timezone.utc),
        )
        db_session.add(session)
        db_session.commit()

        db_session.refresh(session)
        assert session.user is not None
        assert session.user.id == sample_user.id


class TestVerificationTokenModel:
    """Test VerificationToken model."""

    def test_create_verification_token(self, db_session: Session):
        """Test creating a verification token."""
        token = VerificationToken(
            identifier="user@example.com",
            token="verification_token_123",
            expires_at=datetime.now(timezone.utc),
        )
        db_session.add(token)
        db_session.commit()

        assert token.id is not None
        assert token.identifier == "user@example.com"

    def test_verification_token_unique(self, db_session: Session):
        """Test verification token unique constraint."""
        token1 = VerificationToken(
            identifier="user@example.com",
            token="same_token",
            expires_at=datetime.now(timezone.utc),
        )
        db_session.add(token1)
        db_session.commit()

        token2 = VerificationToken(
            identifier="user@example.com",
            token="same_token",  # Same identifier and token
            expires_at=datetime.now(timezone.utc),
        )
        db_session.add(token2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestPasswordHistoryModel:
    """Test PasswordHistory model."""

    def test_create_password_history(self, db_session: Session, sample_user: User):
        """Test creating password history entry."""
        history = PasswordHistory(
            user_id=sample_user.id,
            hashed_password="old_hashed_password",
        )
        db_session.add(history)
        db_session.commit()

        assert history.id is not None
        assert history.user_id == sample_user.id
        assert history.created_at is not None

    def test_password_history_user_relationship(self, db_session: Session, sample_user: User):
        """Test password history user relationship."""
        history = PasswordHistory(
            user_id=sample_user.id,
            hashed_password="hashed_pass",
        )
        db_session.add(history)
        db_session.commit()

        db_session.refresh(history)
        assert history.user is not None
        assert history.user.id == sample_user.id

    def test_password_history_multiple_entries(self, db_session: Session, sample_user: User):
        """Test multiple password history entries for a user."""
        for i in range(3):
            history = PasswordHistory(
                user_id=sample_user.id,
                hashed_password=f"password_{i}",
            )
            db_session.add(history)
        db_session.commit()

        db_session.refresh(sample_user)
        assert len(sample_user.password_history) == 3
