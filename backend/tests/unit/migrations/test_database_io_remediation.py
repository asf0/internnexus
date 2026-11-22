"""Structural tests for the database I/O remediation migrations."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.models import Job, JobBoardSnapshot, PipelineJobSighting, PipelineSyncState
from tests.paths import ALEMBIC_VERSIONS, REPO_ROOT


VERSIONS = ALEMBIC_VERSIONS
REPOSITORY_ROOT = REPO_ROOT


def _load(filename: str):
    path = VERSIONS / filename
    spec = importlib.util.spec_from_file_location(filename.removesuffix(".py"), path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return path, module


def test_sightings_migration_is_additive_and_concurrent() -> None:
    path, migration = _load("0004_pipeline_job_sightings.py")
    source = path.read_text()

    assert migration.down_revision == "0003_jobs_last_seen_sync_indexes"
    assert "pipeline_job_sightings" in source
    assert "sync_id" in source
    assert "fingerprint" in source
    assert "idx_jobs_active_id_sync" in source
    assert "idx_jobs_inactive_id_sync" in source
    assert "postgresql_concurrently=True" in source
    assert '"idx_jobs_active_sync"' not in source


def test_search_trigger_migration_has_change_guard_and_all_source_columns() -> None:
    path, migration = _load("0005_search_vector_change_guard.py")
    source = path.read_text()

    assert migration.down_revision == "0004_pipeline_job_sightings"
    assert "IS NOT DISTINCT FROM" in source
    assert "title, company, location, city, state, country, description_text" in source
    assert "DROP TRIGGER IF EXISTS job_search_vector_trigger" in source


def test_pg_stat_statements_migration_follows_trigger_migration() -> None:
    path, migration = _load("0006_pg_stat_statements.py")
    source = path.read_text()

    assert migration.down_revision == "0005_search_vector_change_guard"
    assert "CREATE EXTENSION IF NOT EXISTS pg_stat_statements" in source


def test_sync_index_contract_is_concurrent_and_reversible() -> None:
    path, migration = _load("0007_jobs_id_sync_contract.py")
    source = path.read_text()

    assert migration.down_revision == "0006_pg_stat_statements"
    assert source.count("postgresql_concurrently=True") == 4
    assert "ALTER INDEX idx_jobs_active_id_sync" in source
    assert "ALTER INDEX idx_jobs_inactive_id_sync" in source
    assert '["last_seen"]' in source
    assert "def downgrade()" in source


def test_backend_metadata_includes_sightings_table() -> None:
    table = PipelineJobSighting.__table__
    assert table.name == "pipeline_job_sightings"
    assert set(table.primary_key.columns.keys()) == {"sync_id", "fingerprint"}


def test_board_snapshot_migration_and_shared_metadata() -> None:
    path, migration = _load("0011_job_board_snapshots.py")
    source = path.read_text()

    assert migration.down_revision == "0010_location_filter_indexes"
    assert "job_board_snapshots" in source
    assert "pipeline_sync_state" in source
    assert "snapshots_bootstrapped" in source
    assert set(JobBoardSnapshot.__table__.primary_key.columns.keys()) == {
        "source",
        "company_slug",
    }
    assert PipelineSyncState.__table__.name == "pipeline_sync_state"


def test_embedding_input_hash_migration_and_shared_metadata() -> None:
    path, migration = _load("0014_embedding_input_hash.py")
    source = path.read_text()

    assert migration.down_revision == "0013_mcp_invocation_analytics"
    assert "embedding_input_hash" in source
    assert "is_active AND description_embedding IS NULL" in source
    assert Job.__table__.c.embedding_input_hash.type.length == 64


def test_production_postgres_tuning() -> None:
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text()
    env_example = (REPOSITORY_ROOT / ".env.example").read_text()

    for setting in (
        "shared_buffers=${POSTGRES_SHARED_BUFFERS:-512MB}",
        "effective_cache_size=${POSTGRES_EFFECTIVE_CACHE_SIZE:-2GB}",
        "random_page_cost=${POSTGRES_RANDOM_PAGE_COST:-1.1}",
        "work_mem=${POSTGRES_WORK_MEM:-8MB}",
        "maintenance_work_mem=${POSTGRES_MAINTENANCE_WORK_MEM:-128MB}",
        "wal_buffers=-1",
        "wal_compression=lz4",
        "max_wal_size=${POSTGRES_MAX_WAL_SIZE:-4GB}",
        "min_wal_size=${POSTGRES_MIN_WAL_SIZE:-512MB}",
        "checkpoint_timeout=30min",
        "checkpoint_completion_target=0.9",
        "synchronous_commit=${POSTGRES_SYNCHRONOUS_COMMIT:-off}",
        "jit=off",
        "shared_preload_libraries=pg_stat_statements",
        "track_io_timing=on",
        "track_wal_io_timing=on",
    ):
        assert setting in compose

    assert "MCP_PUBLIC_URL=http://localhost:8001" in env_example
    assert "POSTGRES_MAX_WAL_SIZE=4GB" in env_example
    assert "POSTGRES_SYNCHRONOUS_COMMIT=off" in env_example

    # Staged-deploy and rollback assertions were removed with the legacy deploy
    # workflow. Restore them against .github/workflows/deploy.yml when the
    # GitHub deployment workflow is added.


def test_last_seen_index_migration_is_concurrent_and_reversible() -> None:
    path, migration = _load("0016_jobs_last_seen_index.py")
    source = path.read_text()

    assert migration.down_revision == "0015_authoritative_sessions"
    assert "idx_jobs_last_seen" in source
    assert '["last_seen"]' in source
    assert "postgresql_concurrently=True" in source
    assert "autocommit_block()" in source
    assert "def downgrade()" in source
    # 0007 replaced the last_seen sync indexes with id-ordered ones, leaving the
    # `since` scoping in cleanup_locations without an index to use. This index
    # restores that capability without resurrecting the partial sync indexes.
    assert "idx_jobs_active_sync" not in source
