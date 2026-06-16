from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.ingest import core as pipeline
from pipeline.domain import JobSchema


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.com/jobs")
    response = httpx.Response(status_code=status_code, request=request)
    return httpx.HTTPStatusError("boom", request=request, response=response)


@pytest.mark.asyncio
async def test_fetch_all_apis_parallel_records_404_cooldown_error(monkeypatch):
    saved_cache: dict[str, dict[str, float]] = {}

    class _Greenhouse404Client:
        def close(self) -> None:
            return None

        def fetch_jobs(self, _slug: str):
            raise _http_status_error(404)

    class _NoopClient:
        def close(self) -> None:
            return None

        def fetch_jobs(self, _slug: str):
            return []

    monkeypatch.setattr(pipeline, "GreenhouseClient", _Greenhouse404Client)
    monkeypatch.setattr(pipeline, "LeverClient", _NoopClient)
    monkeypatch.setattr(pipeline, "AshbyClient", _NoopClient)
    monkeypatch.setattr(pipeline, "get_greenhouse_slugs", lambda: ["missing-gh"])
    monkeypatch.setattr(pipeline, "get_lever_slugs", lambda: [])
    monkeypatch.setattr(pipeline, "get_ashby_slugs", lambda: [])
    monkeypatch.setattr(pipeline, "_load_slug_404_cache", lambda: {})
    monkeypatch.setattr(
        pipeline,
        "_save_slug_404_cache",
        lambda cache: saved_cache.update(cache),
    )

    gh_jobs, lever_jobs, ashby_jobs, errors = await pipeline._fetch_all_apis_parallel(
        not_found_cooldown_hours=2,
        run_id="run-404",
        include_errors=True,
    )

    assert gh_jobs == []
    assert lever_jobs == []
    assert ashby_jobs == []
    assert len(errors) == 1
    assert errors[0]["source"] == "greenhouse"
    assert errors[0]["slug"] == "missing-gh"
    assert errors[0]["status_code"] == 404
    assert errors[0]["error_type"] == "http_404"
    assert errors[0]["run_id"] == "run-404"
    assert errors[0]["cooldown_until"] > time.time()
    assert "missing-gh" in saved_cache.get("greenhouse", {})


@pytest.mark.asyncio
async def test_fetch_all_apis_parallel_non_404_stays_resilient(monkeypatch):
    class _Greenhouse500Client:
        def close(self) -> None:
            return None

        def fetch_jobs(self, _slug: str):
            raise _http_status_error(500)

    class _LeverOkClient:
        def close(self) -> None:
            return None

        def fetch_jobs(self, _slug: str):
            return [
                JobSchema(
                    source="lever",
                    title="Engineer",
                    company="Acme",
                    location="Remote",
                    apply_url="https://example.com",
                    description_text="desc",
                )
            ]

    class _NoopClient:
        def close(self) -> None:
            return None

        def fetch_jobs(self, _slug: str):
            return []

    monkeypatch.setattr(pipeline, "GreenhouseClient", _Greenhouse500Client)
    monkeypatch.setattr(pipeline, "LeverClient", _LeverOkClient)
    monkeypatch.setattr(pipeline, "AshbyClient", _NoopClient)
    monkeypatch.setattr(pipeline, "get_greenhouse_slugs", lambda: ["boom-gh"])
    monkeypatch.setattr(pipeline, "get_lever_slugs", lambda: ["ok-lever"])
    monkeypatch.setattr(pipeline, "get_ashby_slugs", lambda: [])
    monkeypatch.setattr(pipeline, "_load_slug_404_cache", lambda: {})
    monkeypatch.setattr(pipeline, "_save_slug_404_cache", lambda _cache: None)

    gh_jobs, lever_jobs, ashby_jobs, errors = await pipeline._fetch_all_apis_parallel(
        run_id="run-500",
        include_errors=True,
    )

    assert gh_jobs == []
    assert len(lever_jobs) == 1
    assert ashby_jobs == []
    assert len(errors) == 1
    assert errors[0]["source"] == "greenhouse"
    assert errors[0]["slug"] == "boom-gh"
    assert errors[0]["status_code"] == 500
    assert errors[0]["error_type"] == "http_error"


@pytest.mark.asyncio
async def test_fetch_all_apis_parallel_logs_aggregate_failures_with_context(monkeypatch, caplog):
    class _BoomClient:
        def close(self) -> None:
            return None

        def fetch_jobs(self, _slug: str):
            raise RuntimeError("network down")

    class _NoopClient:
        def close(self) -> None:
            return None

        def fetch_jobs(self, _slug: str):
            return []

    monkeypatch.setattr(pipeline, "GreenhouseClient", _BoomClient)
    monkeypatch.setattr(pipeline, "LeverClient", _BoomClient)
    monkeypatch.setattr(pipeline, "AshbyClient", _NoopClient)
    monkeypatch.setattr(pipeline, "get_greenhouse_slugs", lambda: ["gh-1"])
    monkeypatch.setattr(pipeline, "get_lever_slugs", lambda: ["lv-1"])
    monkeypatch.setattr(pipeline, "get_ashby_slugs", lambda: [])
    monkeypatch.setattr(pipeline, "_load_slug_404_cache", lambda: {})
    monkeypatch.setattr(pipeline, "_save_slug_404_cache", lambda _cache: None)

    with caplog.at_level("WARNING"):
        _, _, _, errors = await pipeline._fetch_all_apis_parallel(
            run_id="run-agg",
            include_errors=True,
        )

    assert len(errors) == 2
    summary_records = [
        record for record in caplog.records if "API fetch error summary" in record.getMessage()
    ]
    assert len(summary_records) == 1
    assert getattr(summary_records[0], "step", None) == "ingest"
    assert getattr(summary_records[0], "source", None) == "all"
    assert getattr(summary_records[0], "slug", None) == "*"
    assert getattr(summary_records[0], "run_id", None) == "run-agg"

    slug_error_records = [
        record for record in caplog.records if "Slug fetch failed" in record.getMessage()
    ]
    assert len(slug_error_records) == 2
    assert {getattr(record, "source", None) for record in slug_error_records} == {
        "greenhouse",
        "lever",
    }
    assert {getattr(record, "slug", None) for record in slug_error_records} == {"gh-1", "lv-1"}
    assert {getattr(record, "run_id", None) for record in slug_error_records} == {"run-agg"}


@pytest.mark.asyncio
async def test_fetch_source_jobs_streamed_yields_chunks_and_records_errors(monkeypatch):
    saved_cache: dict[str, dict[str, float]] = {}
    fetched_slugs: list[str] = []

    class _MixedClient:
        def close(self) -> None:
            return None

        def fetch_jobs(self, slug: str):
            fetched_slugs.append(slug)
            if slug == "missing":
                raise _http_status_error(404)
            if slug == "broken":
                raise RuntimeError("boom")
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

    monkeypatch.setattr(pipeline, "_load_slug_404_cache", lambda: {})
    monkeypatch.setattr(
        pipeline,
        "_save_slug_404_cache",
        lambda cache: saved_cache.update(cache),
    )

    chunks = []
    async for chunk in pipeline._fetch_source_jobs_streamed(
        source_name="Greenhouse",
        slugs=["a", "b", "missing", "broken"],
        fetch_func=_MixedClient().fetch_jobs,
        chunk_size=2,
        not_found_cooldown_hours=2,
        run_id="run-stream",
    ):
        chunks.append(chunk)

    assert len(chunks) == 2
    assert len(chunks[0]) == 2  # a, b
    assert len(chunks[1]) == 0  # missing (404), broken (exception)
    assert {job.company for job in chunks[0]} == {"a", "b"}
    assert "missing" in saved_cache.get("greenhouse", {})
    assert fetched_slugs == ["a", "b", "missing", "broken"]
