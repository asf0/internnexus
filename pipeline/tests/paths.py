"""Filesystem anchors for the pipeline test suite.

Mirrors :mod:`pipeline.infra.paths` for tests: one place resolves a location
from ``__file__``, so moving a test between directories can never silently
change which fixture or project root it points at.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["PKG_ROOT", "PROJECT_ROOT", "WORKSPACE_ROOT", "FIXTURES_DIR", "TESTS_DIR"]

#: ``pipeline/tests``
TESTS_DIR = Path(__file__).resolve().parent

#: ``pipeline/`` — the package root.
PKG_ROOT = TESTS_DIR.parent

#: Repository checkout containing ``pipeline/``, ``backend/``, ``frontend/``.
PROJECT_ROOT = PKG_ROOT.parent

#: Directory above the repository; base for filesystem log paths.
WORKSPACE_ROOT = PROJECT_ROOT.parent

#: Golden-fixture JSON lives here.
FIXTURES_DIR = TESTS_DIR / "fixtures"
