from __future__ import annotations

from pipeline.tests.paths import PROJECT_ROOT
import sys
import time
from pathlib import Path

import httpx
import pytest

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.stages.ingest import source_stream as pipeline
from pipeline.domain import JobSchema
from pipeline.domain.sync_result import SourceFetchStats
from pipeline.infra.pipeline_config import ApiConfig, IngestConfig


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.com/jobs")
    response = httpx.Response(status_code=status_code, request=request)
    return httpx.HTTPStatusError("boom", request=request, response=response)


@pytest.mark.asyncio
async def test_fetch_source_jobs_streamed_yields_chunks_and_records_errors(monkeypatch, caplog):
    saved_cache: dict[str, dict[str, float]] = {}
    fetched_slugs: list[str] = []
    stats = SourceFetchStats(source="greenhouse", configured_slugs=4)

    class _MixedClient:
        def close(self) -> None:
            return None

        def fetch_jobs(self, slug: str):
            fetched_slugs.append(slug)
            if slug == "missing":
                raise _http_status_error(404)
            if slug == "broken":
                raise _http_status_error(500)
            return [
                JobSchema(
                    source="greenhouse",
                    title=f"Job at {slug}",
                    company=slug,
                    location="Remote",
                    apply_url=f"https://example.com/{slug}",
                    description_text="desc",
                )
            ]

    monkeypatch.setattr(pipeline, "load_slug_404_cache", lambda: {})
    monkeypatch.setattr(
        pipeline,
        "save_slug_404_cache",
        lambda cache: saved_cache.update(cache),
    )

    boards = []
    with caplog.at_level("WARNING"):
        async for board in pipeline.fetch_source_jobs_streamed(
            source_name="Greenhouse",
            slugs=["a", "b", "missing", "broken"],
            fetch_func=_MixedClient().fetch_jobs,
            chunk_size=2,
            api_fetch_concurrency=ApiConfig().fetch_concurrency,
            not_found_cooldown_hours=2,
            run_id="run-stream",
            stats=stats,
        ):
            boards.append(board)

    assert [board.slug for board in boards] == ["a", "b", "missing", "broken"]
    assert {board.jobs[0].company for board in boards[:2]} == {"a", "b"}
    assert all(not board.jobs for board in boards[2:])
    assert "missing" in saved_cache.get("greenhouse", {})
    # Chunk fetches are concurrent, so completion order is not a contract.
    assert set(fetched_slugs) == {"a", "b", "missing", "broken"}
    assert stats.jobs_fetched == 2
    assert stats.fetch_errors == 2
    assert stats.fatal_errors == 2
    assert stats.complete is False
    fatal_records = [record for record in caplog.records if "Slug fetch failed" in record.getMessage()]
    assert len(fatal_records) == 1
    assert "status=500" in fatal_records[0].getMessage()
    assert getattr(fatal_records[0], "source", None) == "greenhouse"
    assert getattr(fatal_records[0], "slug", None) == "broken"
    assert getattr(fatal_records[0], "run_id", None) == "run-stream"
    summary_records = [record for record in caplog.records if "fetch error summary" in record.getMessage()]
    assert len(summary_records) == 1
    assert getattr(summary_records[0], "step", None) == "ingest"
    assert getattr(summary_records[0], "source", None) == "greenhouse"
    assert getattr(summary_records[0], "slug", None) == "*"
    assert getattr(summary_records[0], "run_id", None) == "run-stream"


@pytest.mark.asyncio
async def test_confirmed_retired_slug_does_not_block_other_company_cleanup(monkeypatch):
    stats = SourceFetchStats(source="greenhouse", configured_slugs=2)
    fetched: list[str] = []

    def fetch(slug: str):
        fetched.append(slug)
        return [
            JobSchema(
                source="greenhouse",
                title="Job",
                company=slug,
                location="Remote",
                apply_url=f"https://example.com/{slug}",
                description_text="desc",
            )
        ]

    monkeypatch.setattr(
        pipeline,
        "load_slug_404_cache",
        lambda: {"greenhouse": {"retired": -(time.time() + 3600)}},
    )
    monkeypatch.setattr(pipeline, "save_slug_404_cache", lambda _cache: None)

    boards = [
        board
        async for board in pipeline.fetch_source_jobs_streamed(
            source_name="Greenhouse",
            slugs=["retired", "active"],
            fetch_func=fetch,
            chunk_size=2,
            api_fetch_concurrency=1,
            not_found_cooldown_hours=1,
            stats=stats,
        )
    ]

    assert fetched == ["active"]
    assert [board.slug for board in boards] == ["retired", "active"]
    assert [job.company for board in boards for job in board.jobs] == ["active"]
    assert boards[0].error is not None
    assert boards[0].error["error_type"] == "http_404_confirmed"
    assert stats.complete is True


@pytest.mark.asyncio
async def test_fetch_source_jobs_streamed_uses_configured_window(monkeypatch):
    api_config = ApiConfig()
    config = IngestConfig()

    def fetch_jobs(slug: str):
        return [
            JobSchema(
                source="greenhouse",
                title=f"Job at {slug}",
                company=slug,
                location="Remote",
                apply_url=f"https://example.com/{slug}",
                description_text="desc",
            )
        ]

    monkeypatch.setattr(pipeline, "load_slug_404_cache", lambda: {})
    monkeypatch.setattr(pipeline, "save_slug_404_cache", lambda _cache: None)

    board_sizes = []
    slugs = [f"company-{index}" for index in range(config.slug_chunk_size + 1)]
    async for board in pipeline.fetch_source_jobs_streamed(
        source_name="Greenhouse",
        slugs=slugs,
        fetch_func=fetch_jobs,
        chunk_size=config.slug_chunk_size,
        api_fetch_concurrency=api_config.fetch_concurrency,
        not_found_cooldown_hours=api_config.slug_404_cooldown_hours,
    ):
        board_sizes.append(len(board.jobs))

    assert board_sizes == [1] * len(slugs)
    assert config.upsert_batch_size == 1000
