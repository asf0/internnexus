"""Structural tests for the database I/O remediation migrations."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.models import PipelineJobSighting


VERSIONS = Path(__file__).resolve().parents[2] / "alembic" / "versions"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


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


def test_production_postgres_tuning_and_staged_deploy_guards() -> None:
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text()
    workflow = (REPOSITORY_ROOT / ".gitea" / "workflows" / "deploy.yml").read_text()

    for setting in (
        "shared_buffers=4GB",
        "wal_buffers=-1",
        "wal_compression=lz4",
        "max_wal_size=8GB",
        "min_wal_size=2GB",
        "checkpoint_timeout=15min",
        "checkpoint_completion_target=0.9",
        "shared_preload_libraries=pg_stat_statements",
        "track_io_timing=on",
        "track_wal_io_timing=on",
    ):
        assert setting in compose

    assert "docker compose up -d --no-recreate db" in workflow
    assert "git clone --depth 2" in workflow
    assert "PIPELINE_MAINTENANCE_MODE" in workflow
    assert "docker compose stop pipeline" in workflow
    assert "docker compose build pipeline" in workflow
    assert "backend/alembic/versions/000[4-7]_" in workflow
