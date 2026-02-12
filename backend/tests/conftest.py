"""Test configuration and fixtures for backend tests."""

from __future__ import annotations

import os
import sys
from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

# Load environment variables from .env file before any app imports
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import Base, get_db
from app.main import app
from app.models import Account, Job, JobCategory, JobSource, User


# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine) -> Generator[Session, None, None]:
    """Create a fresh database session for each test."""
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    # Clear all tables before each test
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()

    yield session

    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with a fresh database session."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_user(db_session: Session) -> User:
    """Create a sample user for testing."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        name="Test User",
        hashed_password="$argon2id$v=19$m=65536,t=3,p=4$TEST_HASH_ONLY$FAKE_HASH_FOR_TESTING",  # test-only fake hash
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_oauth_user(db_session: Session) -> User:
    """Create a sample OAuth user without password."""
    user = User(
        id=uuid4(),
        email="oauth@example.com",
        name="OAuth User",
        hashed_password=None,
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create OAuth account
    account = Account(
        user_id=user.id,
        provider="github",
        provider_account_id="123456",
        access_token="test-fake-oauth-token-NOT-REAL",
    )
    db_session.add(account)
    db_session.commit()

    return user


@pytest.fixture
def sample_job(db_session: Session) -> Job:
    """Create a sample job for testing."""
    job = Job(
        id=uuid4(),
        fingerprint=f"test-fingerprint-{uuid4()}",
        source=JobSource.greenhouse,
        title="Software Engineer Intern",
        company="Test Company",
        location="San Francisco, CA",
        city="San Francisco",
        state="CA",
        country="USA",
        apply_url="https://example.com/apply",
        description_text="This is a test job description.",
        visa_sponsored=True,
        f1_friendly=True,
        job_category=JobCategory.software_engineering,
        is_faang_plus=False,
        is_active=True,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def sample_jobs(db_session: Session) -> list[Job]:
    """Create multiple sample jobs for testing."""
    jobs = [
        Job(
            id=uuid4(),
            fingerprint=f"fingerprint-{i}-{uuid4()}",
            source=JobSource.greenhouse,
            title=f"Job Title {i}",
            company=f"Company {i % 3}",  # 3 different companies
            location=["San Francisco, CA", "New York, NY", "Remote"][i % 3],
            apply_url=f"https://example.com/apply/{i}",
            description_text=f"Description for job {i}",
            visa_sponsored=i % 2 == 0,
            f1_friendly=i % 3 == 0,
            job_category=[
                JobCategory.software_engineering,
                JobCategory.data_science_ai,
                JobCategory.product_management,
            ][i % 3],
            is_faang_plus=i == 0,
            is_active=True,
        )
        for i in range(10)
    ]

    db_session.add_all(jobs)
    db_session.commit()

    for job in jobs:
        db_session.refresh(job)

    return jobs


@pytest.fixture
def auth_headers(sample_user: User) -> dict[str, str]:
    """Generate authorization headers for a user."""
    from app.auth.jwt import create_access_token

    token = create_access_token(data={"sub": str(sample_user.id), "email": sample_user.email})
    return {"Authorization": f"Bearer {token}"}
