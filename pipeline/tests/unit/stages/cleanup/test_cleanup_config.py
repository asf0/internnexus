"""Tests for cleanup config threading and default values."""

from __future__ import annotations

from pipeline.tests.paths import PROJECT_ROOT
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest

from pipeline.stages.cleanup import batch_updater as bp
from pipeline.stages.cleanup import exporter as ex_mod
from pipeline.stages.cleanup import location_parser as parser_mod
from pipeline.infra.pipeline_config import CleanupConfig, Config
import pipeline.runtime.orchestrator.steps as runner_module
from pipeline.runtime.orchestrator import PipelineRunner

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestDefaultConfigValues:
    def test_parse_concurrency_default(self):
        assert CleanupConfig().parse_concurrency == 12

    def test_chunk_size_default(self):
        assert CleanupConfig().chunk_size == 5000

    def test_location_cache_max_size_default(self):
        assert CleanupConfig().location_cache_max_size == 10_000

    def test_warm_batch_default(self):
        assert CleanupConfig().warm_batch == 500

    def test_warm_batch_ge_1(self):
        with pytest.raises(ValueError):
            CleanupConfig(warm_batch=0)


class TestWarmBatchForwarded:
    """warm_batch is passed from PipelineRunner.step_cleanup through to cleanup_locations."""

    @pytest.mark.asyncio
    async def test_warm_batch_reaches_cleanup_locations(self, monkeypatch):
        captured_kwargs: dict = {}

        async def _fake_cleanup(**kwargs):
            captured_kwargs.update(kwargs)
            return 0

        monkeypatch.setattr(runner_module, "cleanup_locations", _fake_cleanup)

        config = Config()
        config.cleanup.warm_batch = 77
        runner = PipelineRunner(
            get_last_completed_run_started_at_func=AsyncMock(return_value=None)
        )
        runner.config = config

        await runner.step_cleanup(state=None)

        assert captured_kwargs.get("warm_batch") == 77
        assert captured_kwargs.get("chunk_size") == 5000
        assert captured_kwargs.get("parse_concurrency") == 12
        assert captured_kwargs.get("location_cache_max_size") == 10_000


class TestNonDefaultTestChunkSize:
    """A non-default chunk_size reaches repository pagination."""

    @pytest.mark.asyncio
    async def test_chunk_size_100_reaches_pagination(self, monkeypatch, tmp_path):
        monkeypatch.setattr(parser_mod, "get_location_cache", Mock(return_value=_FakeCache()))
        fake_file = str(tmp_path / "cleanup" / "exporter.py")
        monkeypatch.setattr(ex_mod, "__file__", fake_file)

        repo = _FakeRepo()
        repo.load([], 1)
        monkeypatch.setattr(ex_mod, "SQLAlchemyJobRepository", lambda _s: repo)

        await ex_mod._process_test_mode_chunked(
            SimpleNamespace(),  # pyright: ignore[reportArgumentType]
            since=None,
            process_all=True,
            limit=None,
            chunk_size=100,
            location_cache_max_size=10_000,
        )

        assert len(repo.pagination_calls) >= 1
        for call in repo.pagination_calls:
            assert call["limit"] == 100, f"Expected limit=100, got {call['limit']}"


class TestNonDefaultWarmBatch:
    """warm_batch controls concurrent parse grouping in production mode."""

    @pytest.mark.asyncio
    async def test_warm_batch_3_groups_parsing(self, monkeypatch):
        gather_sizes: list[int] = []

        async def _tracked_gather(*coros):
            gather_sizes.append(len(coros))
            results = []
            for c in coros:
                results.append(await c)
            return results

        monkeypatch.setattr(bp.asyncio, "gather", _tracked_gather)
        monkeypatch.setattr(parser_mod, "get_location_cache", Mock(return_value=_FakeCache()))

        jobs = [
            SimpleNamespace(
                id=UUID(f"00000000-0000-0000-0000-{i:012d}"),
                source="test",
                location=f"City{i}",
                city=None,
                state=None,
                country=None,
            )
            for i in range(6)
        ]

        repo = _FakeRepo()
        repo.load(jobs, 6)
        monkeypatch.setattr(bp, "SQLAlchemyJobRepository", lambda _s: repo)

        fake_session = SimpleNamespace(expunge_all=lambda: None)

        await bp._process_production_mode_chunked(
            fake_session,  # pyright: ignore[reportArgumentType]
            since=None,
            process_all=True,
            limit=None,
            parse_concurrency=1,
            chunk_size=5000,
            location_cache_max_size=10_000,
            warm_batch=3,
        )

        assert gather_sizes == [3, 3], f"Expected gather batches [3, 3], got {gather_sizes}"


class _FakeCache:
    def __init__(self):
        self._store = {}

    def get(self, location: str):
        return self._store.get(location)

    def set(self, location: str, result) -> None:
        self._store[location] = result


class _FakeRepo:
    def __init__(self):
        self._jobs: list = []
        self._total_count = 0
        self.pagination_calls: list[dict] = []

    def load(self, jobs, total_count):
        self._jobs = list(jobs)
        self._total_count = total_count

    async def get_total_count(self, since, process_all):
        return self._total_count

    async def fetch_jobs_batch_keyset(self, since, process_all, last_id, limit):
        remaining = sorted(self._jobs, key=lambda j: j.id)
        if last_id is not None:
            remaining = [j for j in remaining if j.id > last_id]
        batch = remaining[:limit]
        self.pagination_calls.append(
            {"last_id": str(last_id) if last_id is not None else None, "limit": limit, "count": len(batch)}
        )
        return list(batch)

    async def update_job_locations(self, updates):
        return len(updates)
