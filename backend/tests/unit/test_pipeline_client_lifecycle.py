from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import pipeline


class _FakeClient:
    def __init__(self, _timeout_seconds: float = 20.0):
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def fetch_jobs(self, _slug: str):
        return []


@pytest.mark.asyncio
async def test_fetch_all_apis_parallel_closes_clients_on_success(monkeypatch):
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
    monkeypatch.setattr(pipeline, "_load_slug_404_cache", lambda: {})
    monkeypatch.setattr(pipeline, "_save_slug_404_cache", lambda _cache: None)

    result = await pipeline._fetch_all_apis_parallel()

    assert result == ([], [], [])
    assert len(clients) == 3
    assert all(client.closed for client in clients)


@pytest.mark.asyncio
async def test_fetch_all_apis_parallel_closes_clients_on_failure(monkeypatch):
    clients: list[_FakeClient] = []

    def _client_factory(*_args, **_kwargs):
        client = _FakeClient()
        clients.append(client)
        return client

    monkeypatch.setattr(pipeline, "GreenhouseClient", _client_factory)
    monkeypatch.setattr(pipeline, "LeverClient", _client_factory)
    monkeypatch.setattr(pipeline, "AshbyClient", _client_factory)

    def _boom():
        raise RuntimeError("slug lookup failed")

    monkeypatch.setattr(pipeline, "get_greenhouse_slugs", _boom)

    with pytest.raises(RuntimeError, match="slug lookup failed"):
        await pipeline._fetch_all_apis_parallel()

    assert len(clients) == 3
    assert all(client.closed for client in clients)
