"""Focused tests for pipeline quality implementation hardening."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from pipeline.discovery import company_discovery
from pipeline.embeddings import retry_handler
from pipeline.sources.utils import parse_unix_timestamp


def test_parse_unix_timestamp_returns_timezone_aware_utc():
    parsed = parse_unix_timestamp(0)
    assert parsed is None

    parsed = parse_unix_timestamp(1_700_000_000_000)
    assert parsed is not None
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0


@pytest.mark.asyncio
async def test_discovery_enabled_without_searxng_url_fails_clearly(monkeypatch, tmp_path):
    monkeypatch.setattr(
        company_discovery,
        "get_config",
        lambda: SimpleNamespace(discovery=SimpleNamespace(enabled=True, searxng_url="", timeout=1)),
    )

    with pytest.raises(ValueError, match="searxng_url"):
        await company_discovery.discover_companies(
            output_path=tmp_path / "companies.json",
            progress_path=tmp_path / "progress.json",
        )


@pytest.mark.asyncio
async def test_retry_backoff_includes_jitter(monkeypatch):
    retry_job_id = uuid4()
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    async def fake_process(*_args, **_kwargs):
        return 0, 0, 0, []

    monkeypatch.setattr(retry_handler.random, "uniform", lambda _start, _end: 0.25)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(retry_handler, "_process_with_semaphore", fake_process)

    await retry_handler._process_retry_queue(
        [(retry_job_id, "transient", "failed", 0)],
        embedder=object(),
        db=object(),
        semaphore=asyncio.Semaphore(1),
        batch_size=1,
    )

    assert sleeps == [2.25]


def test_collect_retry_items_preserves_uuid_job_ids():
    job_id = uuid4()
    job = SimpleNamespace(id=job_id)

    retry_queue = retry_handler._collect_retry_items([(job, RuntimeError("temporary"))], [], retry_attempt=1)

    assert retry_queue[0][0] == job_id
