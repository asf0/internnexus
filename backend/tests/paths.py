"""Filesystem anchors for the backend test suite.

The test-suite counterpart to ``app/infra/paths.py``: this is the only module in
``backend/tests/`` allowed to resolve a location from ``__file__``.  Import the
anchors from here so a test can be moved between directories without silently
repointing at the wrong file.

Mirrors ``pipeline/tests/paths.py``.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["TESTS_DIR", "BACKEND_DIR", "REPO_ROOT", "ALEMBIC_VERSIONS", "DOCKER_COMPOSE_FILE"]

# The one and only depth assumption in the suite: this file lives at
# ``backend/tests/paths.py``.
TESTS_DIR = Path(__file__).resolve().parent

#: The ``backend/`` service directory.
BACKEND_DIR = TESTS_DIR.parent

#: Repository checkout containing ``backend/``, ``pipeline/``, ``frontend/``.
REPO_ROOT = BACKEND_DIR.parent

#: Alembic revision scripts, asserted against by the migration tests.
ALEMBIC_VERSIONS = BACKEND_DIR / "alembic" / "versions"

#: Repo-root compose file, asserted against by the deployment tests.
DOCKER_COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"
