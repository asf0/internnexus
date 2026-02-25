"""Shared fixtures for backend tests."""

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app
from app.db import get_db
from app.models import Base
from app.rate_limiter import limiter


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Test database URL - can be overridden via environment variable
# Default connects to localhost, but can be set to container IP
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_db"
)


_DB_WRITE_READY: bool | None = None
_DB_WRITE_READY_REASON: str | None = None


def _is_integration_or_e2e_test(request: pytest.FixtureRequest) -> bool:
    """Return True when test belongs to integration/e2e suites."""
    if request.node.get_closest_marker("integration") or request.node.get_closest_marker("e2e"):
        return True
    test_path = str(getattr(request.node, "fspath", ""))
    return "/tests/integration/" in test_path or "/tests/e2e/" in test_path


async def _get_db_write_capability(engine) -> tuple[bool, str]:
    """Check if the current DB user can write to required integration tables."""
    global _DB_WRITE_READY
    global _DB_WRITE_READY_REASON

    if _DB_WRITE_READY is not None:
        return _DB_WRITE_READY, _DB_WRITE_READY_REASON or "cached"

    privilege_query = text(
        """
        SELECT
            CASE
                WHEN to_regclass('public.users') IS NULL THEN false
                ELSE has_table_privilege(current_user, 'public.users', 'INSERT')
            END AS users_insert,
            CASE
                WHEN to_regclass('public.jobs') IS NULL THEN false
                ELSE has_table_privilege(current_user, 'public.jobs', 'INSERT')
            END AS jobs_insert
        """
    )

    try:
        async with engine.connect() as connection:
            row = (await connection.execute(privilege_query)).mappings().first()
            users_insert = bool(row and row["users_insert"])
            jobs_insert = bool(row and row["jobs_insert"])

        if users_insert and jobs_insert:
            _DB_WRITE_READY = True
            _DB_WRITE_READY_REASON = "users/jobs insert granted"
        else:
            missing = []
            if not users_insert:
                missing.append("users INSERT")
            if not jobs_insert:
                missing.append("jobs INSERT")
            _DB_WRITE_READY = False
            _DB_WRITE_READY_REASON = ", ".join(missing) if missing else "missing write privileges"
    except Exception as exc:
        _DB_WRITE_READY = False
        _DB_WRITE_READY_REASON = f"capability check failed: {exc}"

    return _DB_WRITE_READY, _DB_WRITE_READY_REASON or "unknown"


def run_alembic_migrations(database_url: str):
    """Run alembic migrations using subprocess.

    This is more reliable than using the Python API for tests.
    """
    # Convert async URL to sync URL for alembic
    sync_url = database_url.replace("+asyncpg", "")

    # Change to backend directory where alembic.ini is located
    backend_dir = Path(__file__).parent.parent

    # Use alembic from virtual environment, not system
    venv_dir = backend_dir / ".venv"
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

    print("✓ Alembic migrations completed")


def reset_database(database_url: str):
    """Drop all tables and recreate using Alembic."""
    sync_url = database_url.replace("+asyncpg", "")
    backend_dir = Path(__file__).parent.parent
    venv_dir = backend_dir / ".venv"
    if os.name == "nt":
        alembic_path = venv_dir / "Scripts" / "alembic.exe"
    else:
        alembic_path = venv_dir / "bin" / "alembic"
    alembic_cmd = str(alembic_path) if alembic_path.exists() else "alembic"
    env = os.environ.copy()
    env["DATABASE_URL"] = sync_url

    # Downgrade to base (drop everything)
    subprocess.run(
        [alembic_cmd, "downgrade", "base"],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
    )

    # Upgrade to head (recreate everything)
    run_alembic_migrations(database_url)


@pytest.fixture(scope="session")
async def engine():
    """Create test database engine with Alembic migrations."""
    print(f"\n🔄 Setting up test database: {TEST_DATABASE_URL}")

    # Best effort migration; some local test DB users may not have DDL privileges.
    try:
        run_alembic_migrations(TEST_DATABASE_URL)
    except Exception as e:
        print(f"⚠️  Migration skipped due to permissions or connectivity: {e}")

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    yield engine

    # Cleanup after all tests
    await engine.dispose()


@pytest.fixture
async def db_session(engine, request):
    """Create a fresh database session for a test."""
    use_isolated_schema = False
    schema_name = None

    if _is_integration_or_e2e_test(request):
        is_writable, _ = await _get_db_write_capability(engine)
        use_isolated_schema = not is_writable

    async with engine.connect() as connection:
        if use_isolated_schema:
            schema_name = f"test_{uuid4().hex[:12]}"
            await connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
            await connection.execute(text(f'SET search_path TO "{schema_name}", public'))
            await connection.commit()
            await connection.run_sync(
                lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=False)
            )
            await connection.commit()

        transaction = await connection.begin()
        if schema_name:
            await connection.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))

        async_session = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        async with async_session() as session:
            try:
                yield session
            finally:
                await session.close()

        await transaction.rollback()

        if schema_name:
            await connection.execute(text("RESET search_path"))
            await connection.commit()
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
            await connection.commit()


@pytest.fixture(autouse=True)
def reset_rate_limiter_storage():
    """Ensure rate limiter state does not leak across tests."""
    limiter._storage.reset()


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
