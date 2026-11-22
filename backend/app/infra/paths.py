"""Filesystem anchors for the backend package.

This is the single place that resolves a location from ``__file__``.  Every
other module imports from here, so moving a module between directories can
never silently change which file it reads.

This rule exists because it was broken once: ``app/config.py`` resolved the
repo-root ``.env`` with ``Path(__file__).parents[2]``.  Moving the module one
directory deeper did not raise — it just pointed at ``backend/.env``, and every
setting silently fell back to its default.

Mirrors ``pipeline/infra/paths.py``.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["PACKAGE_ROOT", "SERVICE_ROOT", "REPO_ROOT", "ENV_FILE"]

# The one and only depth assumption in the package: this file lives at
# ``backend/app/infra/paths.py``, so parents[1] is ``backend/app/``.
PACKAGE_ROOT = Path(__file__).resolve().parents[1]

#: The ``backend/`` service directory (holds pyproject.toml, alembic.ini).
SERVICE_ROOT = PACKAGE_ROOT.parent

#: Repository checkout containing ``backend/``, ``pipeline/``, ``frontend/``.
REPO_ROOT = SERVICE_ROOT.parent

#: Shared environment file at the repository root, read by pydantic-settings.
ENV_FILE = REPO_ROOT / ".env"
