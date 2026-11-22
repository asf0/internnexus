"""Golden fixture tests for the streamed ingest orchestrator.

These tests exercise the real ``fetch_and_ingest_streamed`` orchestration with
deterministic fake clients, slug registries, cooldown storage, and upsert
boundaries. Expected ``IngestResult.to_metadata()`` values are loaded from a
fixed JSON fixture; tests do not contain an update-golden mode.
"""

from __future__ import annotations

from pipeline.tests.paths import FIXTURES_DIR, PROJECT_ROOT
import json
import sys
import time
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.domain import JobSchema
from pipeline.stages.ingest import fetch_all as ingest_core
from pipeline.stages.ingest import board_processing, source_stream
from pipeline.stages.ingest.deduplication import deduplicate_jobs
from pipeline.stages.ingest.upsert import UpsertStats


FIXTURES_DIR = FIXTURES_DIR
GOLDEN_CASES_PATH = FIXTURES_DIR / "ingest_golden_cases.json"

SYNC_ID = UUID("12345678-1234-5678-1234-567812345678")


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    """Build a real HTTPStatusError with a real Request/Response pair."""
    request = httpx.Request("GET", "https://example.com/jobs")
    response = httpx.Response(status_code=status_code, request=request)
    return httpx.HTTPStatusError("boom", request=request, response=response)


def _job(
    source: str,
    company: str,
    title: str,
    apply_url: str,
    location: str = "Remote",
) -> JobSchema:
    """Build a minimal valid JobSchema for test payloads."""
    return JobSchema(
        source=source,  # type: ignore[arg-type]
        title=title,
        company=company,
        location=location,
        apply_url=apply_url,
        description_text="A sufficiently long internship description for embedding.",
    )


@pytest.fixture
def golden_cases() -> dict[str, dict[str, Any]]:
    with open(GOLDEN_CASES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def slug_404_cache_store() -> dict[str, dict[str, float]]:
    return {}


@pytest.fixture
def patch_slug_404_cache(monkeypatch, slug_404_cache_store):
    monkeypatch.setattr(source_stream, "load_slug_404_cache", lambda: slug_404_cache_store)
    monkeypatch.setattr(
        source_stream,
        "save_slug_404_cache",
        lambda cache: _clear_and_update(slug_404_cache_store, cache),
    )


def _clear_and_update(store: dict, cache: dict) -> None:
    store.clear()
    store.update(cache)


@pytest.fixture
def fake_upsert_jobs(monkeypatch):
    """Replace upsert_jobs with a deterministic fake that exercises real dedup."""

    async def _upsert(
        _db: Any,
        jobs: list[JobSchema],
        *,
        sync_id: UUID,
        deduplicate: bool = True,
        batch_size: int | None = None,
    ) -> UpsertStats:
        del sync_id, batch_size  # unused by fake
        if not jobs:
            return UpsertStats()
        unique = deduplicate_jobs(jobs) if deduplicate else jobs
        return UpsertStats(seen=len(unique), changed=len(unique))

    monkeypatch.setattr(board_processing, "upsert_jobs", _upsert)


def _make_fake_client_class(
    slug_returns: dict[str, list[JobSchema] | BaseException],
    fetched_slugs: list[str],
    clients: list,
) -> type:
    """Return a fake source client class that replays per-slug returns/exceptions."""

    class _FakeClient:
        def __init__(self, _timeout_seconds: float = 20.0) -> None:
            self.closed = False
            clients.append(self)

        def close(self) -> None:
            self.closed = True

        def fetch_jobs(self, slug: str) -> list[JobSchema]:
            fetched_slugs.append(slug)
            result = slug_returns.get(slug, [])
            if isinstance(result, BaseException):
                raise result
            return result  # type: ignore[return-value]

    return _FakeClient


_SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "happy_path",
        "slugs": {"greenhouse": ["stripe"], "lever": ["stripe"], "ashby": ["notion"]},
        "returns": {
            "greenhouse": {
                "stripe": [
                    _job("greenhouse", "Stripe", "SWE Intern", "https://example.com/gh/stripe/1"),
                    _job("greenhouse", "Stripe", "DS Intern", "https://example.com/gh/stripe/2"),
                ],
            },
            "lever": {
                "stripe": [
                    _job("lever", "Stripe", "SWE Intern", "https://example.com/lever/stripe/1"),
                    _job("lever", "Stripe", "DS Intern", "https://example.com/lever/stripe/2"),
                ],
            },
            "ashby": {
                "notion": [
                    _job("ashby", "Notion", "SWE Intern", "https://example.com/ashby/notion/1"),
                    _job("ashby", "Notion", "DS Intern", "https://example.com/ashby/notion/2"),
                ],
            },
        },
    },
    {
        "name": "existing_cooldown",
        "slugs": {"greenhouse": ["stripe"], "lever": ["stripe"], "ashby": ["notion"]},
        "cooldown": {
            "greenhouse": {"stripe": time.time() + 3600},
        },
        "returns": {
            "greenhouse": {"stripe": []},
            "lever": {
                "stripe": [
                    _job("lever", "Stripe", "SWE Intern", "https://example.com/lever/stripe/1"),
                    _job("lever", "Stripe", "DS Intern", "https://example.com/lever/stripe/2"),
                ],
            },
            "ashby": {
                "notion": [
                    _job("ashby", "Notion", "SWE Intern", "https://example.com/ashby/notion/1"),
                    _job("ashby", "Notion", "DS Intern", "https://example.com/ashby/notion/2"),
                ],
            },
        },
    },
    {
        "name": "new_404",
        "slugs": {"greenhouse": ["missing-gh"], "lever": ["stripe"], "ashby": ["notion"]},
        "returns": {
            "greenhouse": {"missing-gh": _http_status_error(404)},
            "lever": {
                "stripe": [
                    _job("lever", "Stripe", "SWE Intern", "https://example.com/lever/stripe/1"),
                    _job("lever", "Stripe", "DS Intern", "https://example.com/lever/stripe/2"),
                ],
            },
            "ashby": {
                "notion": [
                    _job("ashby", "Notion", "SWE Intern", "https://example.com/ashby/notion/1"),
                    _job("ashby", "Notion", "DS Intern", "https://example.com/ashby/notion/2"),
                ],
            },
        },
    },
    {
        "name": "non_404_per_slug_exception",
        "slugs": {"greenhouse": ["ok-gh", "broken-gh"], "lever": ["stripe"], "ashby": ["notion"]},
        "returns": {
            "greenhouse": {
                "ok-gh": [
                    _job("greenhouse", "Stripe", "SWE Intern", "https://example.com/gh/stripe/1"),
                    _job("greenhouse", "Stripe", "DS Intern", "https://example.com/gh/stripe/2"),
                ],
                "broken-gh": RuntimeError("network down"),
            },
            "lever": {
                "stripe": [
                    _job("lever", "Stripe", "SWE Intern", "https://example.com/lever/stripe/1"),
                    _job("lever", "Stripe", "DS Intern", "https://example.com/lever/stripe/2"),
                ],
            },
            "ashby": {
                "notion": [
                    _job("ashby", "Notion", "SWE Intern", "https://example.com/ashby/notion/1"),
                    _job("ashby", "Notion", "DS Intern", "https://example.com/ashby/notion/2"),
                ],
            },
        },
    },
    {
        "name": "fatal_sync_client_exception",
        "slugs": {"greenhouse": ["broken-gh"], "lever": ["stripe"], "ashby": ["notion"]},
        "returns": {
            "greenhouse": {"broken-gh": RuntimeError("network down")},
            "lever": {
                "stripe": [
                    _job("lever", "Stripe", "SWE Intern", "https://example.com/lever/stripe/1"),
                    _job("lever", "Stripe", "DS Intern", "https://example.com/lever/stripe/2"),
                ],
            },
            "ashby": {
                "notion": [
                    _job("ashby", "Notion", "SWE Intern", "https://example.com/ashby/notion/1"),
                    _job("ashby", "Notion", "DS Intern", "https://example.com/ashby/notion/2"),
                ],
            },
        },
    },
    {
        "name": "dedup",
        "slugs": {"greenhouse": ["stripe"], "lever": [], "ashby": []},
        "returns": {
            "greenhouse": {
                "stripe": [
                    _job("greenhouse", "Stripe", "SWE Intern", "https://example.com/dedup"),
                    _job("greenhouse", "Stripe", "DS Intern", "https://example.com/dedup"),
                ],
            },
            "lever": {},
            "ashby": {},
        },
    },
    {
        "name": "empty_result",
        "slugs": {"greenhouse": ["stripe"], "lever": ["stripe"], "ashby": ["notion"]},
        "returns": {
            "greenhouse": {"stripe": []},
            "lever": {"stripe": []},
            "ashby": {"notion": []},
        },
    },
]


class _FakeSession:
    """Placeholder session; the fake upsert does not touch the database."""


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", _SCENARIOS, ids=lambda s: s["name"])
async def test_ingest_golden_scenario(
    monkeypatch,
    scenario: dict[str, Any],
    golden_cases: dict[str, dict[str, Any]],
    slug_404_cache_store: dict[str, dict[str, float]],
    patch_slug_404_cache: None,
    fake_upsert_jobs: None,
) -> None:
    async def _bootstrap_incomplete(_session: Any) -> bool:
        return False

    async def _persist_snapshot(
        _session: Any,
        _source: str,
        _slug: str,
        _snapshot: Any,
    ) -> None:
        return None

    monkeypatch.setattr(ingest_core, "is_bootstrap_complete", _bootstrap_incomplete)
    monkeypatch.setattr(board_processing, "persist_bootstrap_snapshot", _persist_snapshot)

    clients: list = []
    fetched_slugs_by_source: dict[str, list[str]] = {
        "greenhouse": [],
        "lever": [],
        "ashby": [],
    }

    # Preload any existing cooldown entries requested by the scenario.
    for source, entries in scenario.get("cooldown", {}).items():
        for slug, expires_at in entries.items():
            slug_404_cache_store.setdefault(source, {})[slug] = expires_at

    returns_by_source = scenario["returns"]
    monkeypatch.setattr(
        ingest_core,
        "GreenhouseClient",
        _make_fake_client_class(
            returns_by_source.get("greenhouse", {}),
            fetched_slugs_by_source["greenhouse"],
            clients,
        ),
    )
    monkeypatch.setattr(
        ingest_core,
        "LeverClient",
        _make_fake_client_class(
            returns_by_source.get("lever", {}),
            fetched_slugs_by_source["lever"],
            clients,
        ),
    )
    monkeypatch.setattr(
        ingest_core,
        "AshbyClient",
        _make_fake_client_class(
            returns_by_source.get("ashby", {}),
            fetched_slugs_by_source["ashby"],
            clients,
        ),
    )

    monkeypatch.setattr(ingest_core, "get_greenhouse_slugs", lambda: scenario["slugs"]["greenhouse"])
    monkeypatch.setattr(ingest_core, "get_lever_slugs", lambda: scenario["slugs"]["lever"])
    monkeypatch.setattr(ingest_core, "get_ashby_slugs", lambda: scenario["slugs"]["ashby"])

    result = await ingest_core.fetch_and_ingest_streamed(
        cast(AsyncSession, _FakeSession()),
        chunk_size=10,
        upsert_batch_size=100,
        api_fetch_concurrency=5,
        not_found_cooldown_hours=24,
        sync_id=SYNC_ID,
    )

    expected = golden_cases[scenario["name"]]
    actual = result.to_metadata()
    assert {key: actual[key] for key in expected} == expected
    assert result.snapshot_bootstrap is True
    assert result.snapshot_mode is False

    # Scenario-specific behavioral assertions.
    if scenario["name"] == "existing_cooldown":
        assert "stripe" not in fetched_slugs_by_source["greenhouse"]
    elif scenario["name"] == "new_404":
        assert "missing-gh" in slug_404_cache_store.get("greenhouse", {})
    elif scenario["name"] == "non_404_per_slug_exception":
        assert "ok-gh" in fetched_slugs_by_source["greenhouse"]
        assert "broken-gh" in fetched_slugs_by_source["greenhouse"]
    elif scenario["name"] == "fatal_sync_client_exception":
        assert "broken-gh" in fetched_slugs_by_source["greenhouse"]
    elif scenario["name"] == "dedup":
        assert fetched_slugs_by_source["greenhouse"] == ["stripe"]
        assert fetched_slugs_by_source["lever"] == []
        assert fetched_slugs_by_source["ashby"] == []

    assert len(clients) == 3
    assert all(client.closed for client in clients)


@pytest.mark.asyncio
async def test_mark_stale_jobs_inactive_forwards_parameters(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    async def _batched(
        session: Any,
        sync_id: UUID,
        *,
        commit: bool = True,
        batch_size: int | None = None,
        max_attempts: int | None = None,
        base_delay: float | None = None,
        max_delay: float | None = None,
    ) -> int:
        calls.append(
            {
                "session": session,
                "sync_id": sync_id,
                "commit": commit,
                "batch_size": batch_size,
                "max_attempts": max_attempts,
                "base_delay": base_delay,
                "max_delay": max_delay,
            }
        )
        return 42

    monkeypatch.setattr(ingest_core, "batched_mark_stale_jobs_inactive", _batched)

    session = cast(AsyncSession, _FakeSession())
    result = await ingest_core.mark_stale_jobs_inactive(
        session,
        SYNC_ID,
        batch_size=100,
        max_attempts=5,
        base_delay=0.1,
        max_delay=1.0,
    )

    assert result == 42
    assert len(calls) == 1
    assert calls[0]["session"] is session
    assert calls[0]["sync_id"] == SYNC_ID
    assert calls[0]["batch_size"] == 100
    assert calls[0]["max_attempts"] == 5
    assert calls[0]["base_delay"] == 0.1
    assert calls[0]["max_delay"] == 1.0
