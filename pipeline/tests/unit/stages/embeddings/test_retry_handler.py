"""Retry-queue behaviour for the embedding stage."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from pipeline.stages.embeddings import retry_handler
from pipeline.stages.embeddings.batch_records import classify_failures
from internnexus_core.embedding import EmbeddingError


@pytest.mark.asyncio
async def test_retry_backoff_includes_jitter(monkeypatch):
    retry_job_id = uuid4()
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    async def fake_process(*_args, **_kwargs):
        return 0, 0, 0, []

    monkeypatch.setattr(
        retry_handler,
        "delay_for_attempt",
        lambda _policy, _attempt: 2.25,
    )
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


def test_classify_failures_preserves_uuid_job_ids():
    job_id = uuid4()

    retryable, permanent = classify_failures([(job_id, EmbeddingError("temporary", retryable=True))])

    assert retryable[0][0] == job_id
    assert permanent == set()
