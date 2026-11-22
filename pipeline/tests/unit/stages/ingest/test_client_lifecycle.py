from __future__ import annotations

from pipeline.tests.paths import PROJECT_ROOT
import sys
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.stages.ingest import fetch_all as pipeline
from pipeline.stages.ingest import board_processing, source_stream
from pipeline.domain import JobSchema


class _FakeClient:
    def __init__(self, _timeout_seconds: float = 20.0):
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def fetch_jobs(self, slug: str):
        return [
            JobSchema(
                source="greenhouse",
                title="Engineer",
                company=slug,
                location="Remote",
                apply_url=f"https://example.com/{slug}",
                description_text="desc",
            )
        ]


@pytest.mark.asyncio
async def test_streamed_ingest_closes_clients_on_success(monkeypatch):
    clients: list[_FakeClient] = []

    def _client_factory(*_args, **_kwargs):
        client = _FakeClient()
        clients.append(client)
        return client

    monkeypatch.setattr(pipeline, "GreenhouseClient", _client_factory)
    monkeypatch.setattr(pipeline, "LeverClient", _client_factory)
    monkeypatch.setattr(pipeline, "AshbyClient", _client_factory)
    monkeypatch.setattr(pipeline, "get_greenhouse_slugs", lambda: [])
    monkeypatch.setattr(pipeline, "get_lever_slugs", lambda: [])
    monkeypatch.setattr(pipeline, "get_ashby_slugs", lambda: [])
    monkeypatch.setattr(source_stream, "load_slug_404_cache", lambda: {})
    monkeypatch.setattr(source_stream, "save_slug_404_cache", lambda _cache: None)

    async def _bootstrap_complete(_db):
        return True

    monkeypatch.setattr(pipeline, "is_bootstrap_complete", _bootstrap_complete)

    result = await pipeline.fetch_and_ingest_streamed(
        cast(AsyncSession, object()),
        chunk_size=10,
        upsert_batch_size=10,
        api_fetch_concurrency=1,
        not_found_cooldown_hours=1,
        sync_id=uuid4(),
    )

    assert result.total_fetched == 0
    assert len(clients) == 3
    assert all(client.closed for client in clients)


@pytest.mark.asyncio
async def test_streamed_ingest_closes_clients_on_failure(monkeypatch):
    clients: list[_FakeClient] = []

    def _client_factory(*_args, **_kwargs):
        client = _FakeClient()
        clients.append(client)
        return client

    monkeypatch.setattr(pipeline, "GreenhouseClient", _client_factory)
    monkeypatch.setattr(pipeline, "LeverClient", _client_factory)
    monkeypatch.setattr(pipeline, "AshbyClient", _client_factory)

    monkeypatch.setattr(pipeline, "get_greenhouse_slugs", lambda: ["acme"])
    monkeypatch.setattr(pipeline, "get_lever_slugs", lambda: [])
    monkeypatch.setattr(pipeline, "get_ashby_slugs", lambda: [])
    monkeypatch.setattr(source_stream, "load_slug_404_cache", lambda: {})
    monkeypatch.setattr(source_stream, "save_slug_404_cache", lambda _cache: None)

    async def _bootstrap_incomplete(_db):
        return False

    monkeypatch.setattr(pipeline, "is_bootstrap_complete", _bootstrap_incomplete)

    async def _fail_upsert(*_args, **_kwargs):
        raise RuntimeError("upsert failed")

    monkeypatch.setattr(board_processing, "upsert_jobs", _fail_upsert)

    with pytest.raises(RuntimeError, match="upsert failed"):
        await pipeline.fetch_and_ingest_streamed(
            cast(AsyncSession, object()),
            chunk_size=10,
            upsert_batch_size=10,
            api_fetch_concurrency=1,
            not_found_cooldown_hours=1,
            sync_id=uuid4(),
        )

    assert len(clients) == 3
    assert all(client.closed for client in clients)
