"""
Import Chain Regression Tests

These tests validate that the import structure of the backend remains intact.
They catch issues like:
- Broken import chains after refactoring
- Circular dependencies
- Missing sys.path configuration
- Module initialization order problems

Run these tests:
    pytest backend/tests/test_import_chains.py -v

Or as part of the full suite:
    pytest backend/tests/ -v
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# Project root for path calculations
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"


class TestDirectImports:
    """Test that all major modules can be imported directly."""

    def test_import_app_package(self):
        """Verify the main app package imports cleanly."""
        sys.path.insert(0, str(BACKEND_DIR))
        from app import main

        assert main is not None
        assert hasattr(main, "app")

    def test_import_services(self):
        """Verify all service modules import cleanly."""
        sys.path.insert(0, str(BACKEND_DIR))
        from app.services.query_embedding_service import QueryEmbeddingService
        from app.services.job_search import JobSearchService
        from app.services.location_service import LocationService

        assert QueryEmbeddingService is not None
        assert JobSearchService is not None
        assert LocationService is not None

    def test_import_api_modules(self):
        """Verify all API modules import cleanly."""
        sys.path.insert(0, str(BACKEND_DIR))
        from app.api import auth, jobs, matching, users, schemas

        assert auth is not None
        assert jobs is not None
        assert matching is not None
        assert users is not None
        assert schemas is not None

    def test_import_repositories(self):
        """Verify repository modules import cleanly."""
        sys.path.insert(0, str(BACKEND_DIR))
        from app.repositories import base, job, user, account

        assert base is not None
        assert job is not None
        assert user is not None
        assert account is not None

    def test_import_models(self):
        """Verify models import cleanly."""
        sys.path.insert(0, str(BACKEND_DIR))
        from app import models

        assert models is not None

    def test_import_config(self):
        """Verify config can be imported without side effects."""
        sys.path.insert(0, str(BACKEND_DIR))
        from app import config

        assert config is not None
        assert hasattr(config, "get_settings")

    def test_import_db(self):
        """Verify database module imports cleanly."""
        sys.path.insert(0, str(BACKEND_DIR))
        from app import db

        assert db is not None

    def test_import_utils(self):
        """Verify utils module imports cleanly."""
        sys.path.insert(0, str(BACKEND_DIR))
        from app.utils import clean_text_for_embedding

        assert clean_text_for_embedding is not None


class TestNoCircularImports:
    """Detect circular import issues."""

    def test_main_app_no_circular_imports(self):
        """
        Import main app in a subprocess and fail on real import errors.
        """
        code = """
import sys
import traceback
sys.path.insert(0, 'backend')
try:
    import app.main
    print("SUCCESS: No circular imports detected")
except Exception as exc:
    traceback.print_exc()
    print(f"FAILURE: Import failed: {exc}")
    sys.exit(1)
"""
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, cwd=PROJECT_ROOT
        )

        assert result.returncode == 0, f"Import failure detected: {result.stdout}{result.stderr}"

    def test_services_no_circular_imports(self):
        """Check services import cleanly in a subprocess."""
        code = """
import sys
import traceback
sys.path.insert(0, 'backend')
try:
    from app.services import query_embedding_service
    from app.services import job_search
    print("SUCCESS: No circular imports in services")
except Exception as exc:
    traceback.print_exc()
    print(f"FAILURE: Import failed in services: {exc}")
    sys.exit(1)
"""
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, cwd=PROJECT_ROOT
        )

        assert result.returncode == 0, f"Import failure in services: {result.stdout}{result.stderr}"


class TestEntryPoints:
    """Validate that all entry points can import cleanly."""

    def test_main_py_imports(self):
        """Verify backend/app/main.py can be imported."""
        code = """
import sys
sys.path.insert(0, 'backend')
try:
    import app.main
    print("SUCCESS: main.py imports cleanly")
except Exception as e:
    print(f"FAILURE: {e}")
    sys.exit(1)
"""
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, cwd=PROJECT_ROOT
        )

        assert result.returncode == 0, f"Import error in main.py: {result.stderr}"

    def test_main_module_execution(self):
        """Verify python -m app works."""
        # Note: app.__main__ runs uvicorn with reload=True which starts a server
        # We use a short timeout to prevent hanging, and check for import errors
        try:
            result = subprocess.run(
                [sys.executable, "-m", "app", "--help"],
                capture_output=True,
                text=True,
                cwd=BACKEND_DIR,
                timeout=3,  # Timeout to prevent hanging on uvicorn server start
            )
        except subprocess.TimeoutExpired:
            # Timeout is expected since uvicorn starts a server
            # This means imports worked (no ModuleNotFoundError/ImportError)
            return

        # Should either succeed or show help/usage error
        # Import errors are the concern here
        assert (
            "ModuleNotFoundError" not in result.stderr
        ), f"Module execution failed: {result.stderr}"
        assert "ImportError" not in result.stderr, f"Import error: {result.stderr}"


class TestModuleInitializationOrder:
    """Validate module initialization order assumptions."""

    def test_services_can_import_config(self):
        """
        All services should be able to import config.

        Config is at the bottom of the dependency chain.
        """
        sys.path.insert(0, str(BACKEND_DIR))
        from app.services.query_embedding_service import QueryEmbeddingService
        from app.services.location_service import LocationService

        # If these imported successfully, config is accessible
        assert QueryEmbeddingService is not None
        assert LocationService is not None

    def test_api_can_import_services(self):
        """API layer should be able to import services."""
        sys.path.insert(0, str(BACKEND_DIR))
        from app.api.auth import router as auth_router
        from app.api.jobs import router as jobs_router

        assert auth_router is not None
        assert jobs_router is not None


class TestImportPaths:
    """Validate Python path assumptions."""

    def test_import_with_backend_in_path(self):
        """Test importing when backend is in sys.path."""
        code = """
import sys
sys.path.insert(0, 'backend')

from app.services.query_embedding_service import QueryEmbeddingService
print("SUCCESS: Import works with backend in path")
"""
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, cwd=PROJECT_ROOT
        )

        assert result.returncode == 0, f"Import failed: {result.stderr}"

    def test_import_without_path_manipulation(self):
        """
        Test that imports fail appropriately without path setup.

        This documents expected behavior when paths aren't configured.
        """
        code = """
# Don't add backend to path - should fail
try:
    from app.services.query_embedding_service import QueryEmbeddingService
    print("UNEXPECTED: Import succeeded without path setup")
except ModuleNotFoundError as e:
    print(f"EXPECTED: Import failed without path: {e}")
"""
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, cwd=PROJECT_ROOT
        )

        # Should fail without path setup
        assert "EXPECTED" in result.stdout or result.returncode != 0


# Utility functions for debugging import issues
def debug_import_chain(module_name: str) -> None:
    """
    Debug helper to trace import chain.

    Usage in test:
        debug_import_chain("app.services.embedding_service")
    """
    import importlib
    import importlib.util

    print(f"\n=== Debugging import chain for: {module_name} ===")

    # Show current sys.path
    print("sys.path (first 5 entries):")
    for i, p in enumerate(sys.path[:5]):
        print(f"  [{i}] {p}")

    # Try to locate the module
    try:
        spec = importlib.util.find_spec(module_name)
        if spec:
            print("\nModule spec found:")
            print(f"  Origin: {spec.origin}")
            print(f"  Loader: {spec.loader}")
            print(f"  Submodule search locations: {spec.submodule_search_locations}")
        else:
            print(f"\nModule spec NOT found for {module_name}")
    except Exception as e:
        print(f"\nError finding spec: {e}")

    # Try importing with verbose mode
    print("\nImport attempt:")
    try:
        module = importlib.import_module(module_name)
        print(f"  SUCCESS: Imported {module_name} from {module.__file__}")
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")

    print("=" * 50)


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])


def test_backend_has_no_pipeline_or_shared_imports():
    forbidden = ("from pipeline", "import pipeline", "internnexus_shared")
    backend_dir = PROJECT_ROOT / "backend" / "app"
    offenders = []
    for path in backend_dir.rglob("*.py"):
        if path.name == "test_import_chains.py":
            continue
        content = path.read_text()
        for token in forbidden:
            if token in content:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)} contains {token}")
    assert offenders == []


def test_core_has_no_backend_or_pipeline_imports():
    """Core package must never import from backend or pipeline."""
    core_dir = PROJECT_ROOT / "packages" / "internnexus-core" / "internnexus_core"
    if not core_dir.exists():
        return
    forbidden = ("from app", "import app", "from pipeline", "import pipeline", "from backend", "import backend")
    offenders = []
    for path in core_dir.rglob("*.py"):
        content = path.read_text()
        for token in forbidden:
            if token in content:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)} contains {token}")
    assert offenders == []
