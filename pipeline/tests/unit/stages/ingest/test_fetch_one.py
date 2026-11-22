"""Focused unit tests for the shared per-slug fetch helper."""

from __future__ import annotations

from pipeline.tests.paths import PROJECT_ROOT
import asyncio
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.domain import JobSchema
from pipeline.stages.ingest.fetch_one import fetch_one


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.com/jobs")
    response = httpx.Response(status_code=status_code, request=request)
    return httpx.HTTPStatusError("boom", request=request, response=response)


def _job(apply_url: str = "https://example.com/job/1") -> JobSchema:
    return JobSchema(
        source="greenhouse",
        title="SWE Intern",
        company="Stripe",
        location="Remote",
        apply_url=apply_url,
        description_text="A sufficiently long internship description for embedding.",
    )


def _happy_fetch_func(_slug: str) -> list[JobSchema]:
    return [
        _job("https://example.com/job/1"),
        _job("https://example.com/job/2"),
    ]


@pytest.mark.asyncio
async def test_fetch_one_happy_path_returns_jobs_no_error() -> None:
    jobs, error = await fetch_one(
        slug="stripe",
        fetch_func=_happy_fetch_func,
        semaphore=asyncio.Semaphore(2),
        source_name="Greenhouse",
        source_404_cache={},
        cache_lock=asyncio.Lock(),
        cooldown_hours=24,
        run_id="run-1",
    )

    assert len(jobs) == 2
    assert error is None


@pytest.mark.asyncio
async def test_fetch_one_404_records_cooldown_and_error() -> None:
    cache: dict[str, float] = {}

    def _404(_slug: str) -> list[JobSchema]:
        raise _http_status_error(404)

    jobs, error = await fetch_one(
        slug="missing",
        fetch_func=_404,
        semaphore=asyncio.Semaphore(1),
        source_name="Greenhouse",
        source_404_cache=cache,
        cache_lock=asyncio.Lock(),
        cooldown_hours=2,
        run_id="run-404",
    )

    assert jobs == []
    assert error is not None
    assert error["error_type"] == "http_404"
    assert error["source"] == "greenhouse"
    assert error["slug"] == "missing"
    assert error.get("status_code") == 404
    assert error.get("run_id") == "run-404"
    assert "cooldown_until" in error
    assert "missing" in cache
    assert cache["missing"] > time.time()


@pytest.mark.asyncio
async def test_fetch_one_second_404_confirms_retired_slug() -> None:
    cache = {"missing": time.time() - 1}

    def _404(_slug: str) -> list[JobSchema]:
        raise _http_status_error(404)

    jobs, error = await fetch_one(
        slug="missing",
        fetch_func=_404,
        semaphore=asyncio.Semaphore(1),
        source_name="Greenhouse",
        source_404_cache=cache,
        cache_lock=asyncio.Lock(),
        cooldown_hours=2,
        run_id="run-confirm",
    )

    assert jobs == []
    assert error is not None
    assert error["error_type"] == "http_404_confirmed"
    assert cache["missing"] < -time.time()


@pytest.mark.asyncio
async def test_fetch_one_success_clears_prior_404_marker() -> None:
    cache = {"restored": time.time() - 1}

    jobs, error = await fetch_one(
        slug="restored",
        fetch_func=_happy_fetch_func,
        semaphore=asyncio.Semaphore(1),
        source_name="Greenhouse",
        source_404_cache=cache,
        cache_lock=asyncio.Lock(),
        cooldown_hours=2,
        run_id="run-restored",
    )

    assert len(jobs) == 2
    assert error is None
    assert "restored" not in cache


@pytest.mark.asyncio
async def test_fetch_one_non_404_http_error_records_error_no_cache_mutation() -> None:
    existing_expiry = time.time() + 999
    cache: dict[str, float] = {"existing": existing_expiry}

    def _500(_slug: str) -> list[JobSchema]:
        raise _http_status_error(500)

    jobs, error = await fetch_one(
        slug="broken",
        fetch_func=_500,
        semaphore=asyncio.Semaphore(1),
        source_name="Lever",
        source_404_cache=cache,
        cache_lock=asyncio.Lock(),
        cooldown_hours=24,
        run_id="run-500",
    )

    assert jobs == []
    assert error is not None
    assert error["error_type"] == "http_error"
    assert error["source"] == "lever"
    assert error.get("status_code") == 500
    assert "broken" not in cache
    assert cache.get("existing") == existing_expiry


@pytest.mark.asyncio
async def test_fetch_one_generic_exception_records_error_no_cache_mutation() -> None:
    cache: dict[str, float] = {}

    def _boom(_slug: str) -> list[JobSchema]:
        raise RuntimeError("network down")

    jobs, error = await fetch_one(
        slug="broken",
        fetch_func=_boom,
        semaphore=asyncio.Semaphore(1),
        source_name="Ashby",
        source_404_cache=cache,
        cache_lock=asyncio.Lock(),
        cooldown_hours=24,
        run_id="run-boom",
    )

    assert jobs == []
    assert error is not None
    assert error["error_type"] == "exception"
    assert error["source"] == "ashby"
    assert error.get("status_code") is None
    assert "broken" not in cache


@pytest.mark.asyncio
async def test_fetch_one_semaphore_serializes_concurrent_calls() -> None:
    semaphore = asyncio.Semaphore(1)
    first_started = threading.Event()
    release_first = threading.Event()
    second_started = threading.Event()

    def _record(slug: str) -> list[JobSchema]:
        if slug == "a":
            first_started.set()
            if not release_first.wait(timeout=2):
                raise TimeoutError("test did not release the first fetch")
        else:
            second_started.set()
        return []

    first_task = asyncio.create_task(
        fetch_one(
            slug="a",
            fetch_func=_record,
            semaphore=semaphore,
            source_name="Greenhouse",
            source_404_cache={},
            cache_lock=asyncio.Lock(),
            cooldown_hours=24,
            run_id=None,
        )
    )
    second_task = None
    try:
        for _ in range(100):
            if first_started.is_set():
                break
            await asyncio.sleep(0.005)
        assert first_started.is_set()

        second_task = asyncio.create_task(
            fetch_one(
                slug="b",
                fetch_func=_record,
                semaphore=semaphore,
                source_name="Greenhouse",
                source_404_cache={},
                cache_lock=asyncio.Lock(),
                cooldown_hours=24,
                run_id=None,
            )
        )
        await asyncio.sleep(0.05)
        assert not second_started.is_set()
    finally:
        release_first.set()
        if second_task is None:
            await first_task
        else:
            await asyncio.gather(first_task, second_task)

    assert second_started.is_set()
