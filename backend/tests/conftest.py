"""Shared fixtures for backend tests."""

import os
import subprocess
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.db import get_db


# Test database URL - can be overridden via environment variable
# Default connects to localhost, but can be set to container IP
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_db"
)


def run_alembic_migrations(database_url: str):
    """Run alembic migrations using subprocess.

    This is more reliable than using the Python API for tests.
    """
    # Convert async URL to sync URL for alembic
    sync_url = database_url.replace("+asyncpg", "")

    # Change to backend directory where alembic.ini is located
    backend_dir = Path(__file__).parent.parent

    # Use alembic from virtual environment, not system
    venv_dir = backend_dir.parent / ".venv"
    if os.name == "nt":  # Windows
        alembic_path = venv_dir / "Scripts" / "alembic.exe"
    else:
        alembic_path = venv_dir / "bin" / "alembic"

    # Fallback to just 'alembic' if venv path doesn't exist
    alembic_cmd = str(alembic_path) if alembic_path.exists() else "alembic"

    # Set environment variable for alembic to use
    env = os.environ.copy()
    env["DATABASE_URL"] = sync_url
    # Override the .env file settings
    env["POSTGRES_DB"] = "test_db"

    result = subprocess.run(
        [alembic_cmd, "upgrade", "head"],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Alembic stdout: {result.stdout}")
        print(f"Alembic stderr: {result.stderr}")
        raise RuntimeError(f"Alembic migration failed: {result.stderr}")

    print(f"✓ Alembic migrations completed")


def reset_database(database_url: str):
    """Drop all tables and recreate using Alembic."""
    sync_url = database_url.replace("+asyncpg", "")
    backend_dir = Path(__file__).parent.parent
    env = os.environ.copy()
    env["DATABASE_URL"] = sync_url

    # Downgrade to base (drop everything)
    subprocess.run(
        ["alembic", "downgrade", "base"],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
    )

    # Upgrade to head (recreate everything)
    run_alembic_migrations(database_url)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    """Create test database engine with Alembic migrations."""
    print(f"\n🔄 Setting up test database: {TEST_DATABASE_URL}")

    # Run Alembic migrations before creating engine
    try:
        run_alembic_migrations(TEST_DATABASE_URL)
    except Exception as e:
        print(f"⚠️  Migration failed, trying to create database: {e}")
        # If migrations fail, the database might not exist
        # We'll let the engine creation fail naturally with a clear error

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    yield engine

    # Cleanup after all tests
    await engine.dispose()


@pytest.fixture
async def db_session(engine):
    """Create a fresh database session for a test."""
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        yield session
        # Rollback after test
        await session.rollback()


@pytest.fixture
async def client(db_session):
    """Create test HTTP client with database session."""
    from httpx import ASGITransport

    # Override dependency to use test session
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Clear override after test
    app.dependency_overrides.clear()


@pytest.fixture
def mock_user():
    """Return mock user data."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "securepassword123",
        "full_name": "Test User",
    }


@pytest.fixture
def mock_job():
    """Return mock job data."""
    return {
        "title": "Software Engineer",
        "company": "TechCorp",
        "location": "San Francisco, CA",
        "description": "Build awesome software",
        "requirements": ["Python", "FastAPI", "PostgreSQL"],
        "job_type": "full-time",
        "salary_min": 100000,
        "salary_max": 150000,
    }


# Import fixtures from test modules
pytest_plugins = []
