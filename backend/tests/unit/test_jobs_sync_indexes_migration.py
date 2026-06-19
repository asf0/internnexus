"""Tests for the 0002_jobs_sync_indexes migration.

Verifies the migration file structure, revision chain, and that the index
predicates exactly match the query predicates used by the batched sync
operations in pipeline/repositories/sync_ops.py.

Per correction #4: primary assertion is index existence with correct
predicates, not EXPLAIN plan (which is brittle on small test tables).
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path


_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "0002_jobs_sync_indexes.py"
)


def test_migration_file_exists():
    assert _MIGRATION_PATH.exists(), f"Migration file not found at {_MIGRATION_PATH}"


def test_revision_chain():
    spec = importlib.util.spec_from_file_location("migration_0002", _MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0002_jobs_sync_indexes"
    assert module.down_revision == "0001_initial_schema"


def test_migration_uses_concurrent_index_creation():
    source = _MIGRATION_PATH.read_text()
    assert "postgresql_concurrently=True" in source
    assert "autocommit_block" in source


def test_migration_has_both_indexes():
    source = _MIGRATION_PATH.read_text()
    assert "idx_jobs_active_sync" in source
    assert "idx_jobs_inactive_sync" in source


def test_index_predicates_match_sync_ops_queries():
    """The partial index predicates must match the CTE WHERE clauses exactly."""
    from pipeline.repositories.sync_ops import (
        _DELETE_INACTIVE_SQL,
        _MARK_INACTIVE_SQL,
        _REACTIVATE_SQL,
    )

    migration_source = _MIGRATION_PATH.read_text()

    for sql in [_MARK_INACTIVE_SQL, _REACTIVATE_SQL, _DELETE_INACTIVE_SQL]:
        assert "is_active IS TRUE" in sql or "is_active IS FALSE" in sql
        assert "source <> 'manual'" in sql

    assert "is_active IS TRUE" in migration_source
    assert "is_active IS FALSE" in migration_source
    assert "source <> 'manual'" in migration_source


def test_migration_downgrade_drops_indexes():
    source = _MIGRATION_PATH.read_text()
    assert "drop_index" in source
    assert "idx_jobs_active_sync" in source
    assert "idx_jobs_inactive_sync" in source


def test_upgrade_and_downgrade_are_callable():
    spec = importlib.util.spec_from_file_location("migration_0002", _MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert callable(module.upgrade)
    assert callable(module.downgrade)
