from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pipeline.discovery import company_discovery


def test_extract_company_slug_supports_supported_ats_domains():
    assert company_discovery.extract_company_slug("https://jobs.lever.co/stripe/123", "lever") == "stripe"
    assert (
        company_discovery.extract_company_slug("https://boards.greenhouse.io/databricks/jobs/456", "greenhouse")
        == "databricks"
    )
    assert company_discovery.extract_company_slug("https://jobs.ashbyhq.com/openai/abcd", "ashby") == "openai"
    assert company_discovery.extract_company_slug("https://example.com/openai/abcd", "ashby") is None


@pytest.mark.asyncio
async def test_discover_companies_uses_searxng_results_and_persists(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "discovered_companies.json"
    progress_path = tmp_path / "discovery_progress.json"

    config = SimpleNamespace(
        discovery=SimpleNamespace(
            enabled=True,
            timeout=5,
            searxng_url="http://192.168.0.5:8080/search",
            query_delay_seconds=0.0,
            max_pages=None,
        )
    )
    monkeypatch.setattr(company_discovery, "get_config", lambda: config)
    monkeypatch.setattr(company_discovery, "DEFAULT_COUNTRIES", ["United States"])

    async def _fake_search(_client, _base_url: str, query: str, *, page: int = 1) -> list[str]:
        if "jobs.lever.co" in query and page == 1:
            return ["https://jobs.lever.co/stripe/123", "https://jobs.lever.co/openai/456"]
        if "jobs.lever.co" in query and page == 2:
            return ["https://jobs.lever.co/linear/789"]
        if "boards.greenhouse.io" in query and page == 1:
            return ["https://boards.greenhouse.io/databricks/jobs/789"]
        if "jobs.ashbyhq.com" in query and page == 1:
            return ["https://jobs.ashbyhq.com/anthropic/abc"]
        return []

    monkeypatch.setattr(company_discovery, "_search_searxng", _fake_search)

    results = await company_discovery.discover_companies(output_path=output_path, progress_path=progress_path)

    assert results["lever"] == {"stripe", "openai", "linear"}
    assert results["greenhouse"] == {"databricks"}
    assert results["ashby"] == {"anthropic"}

    saved_output = json.loads(output_path.read_text())
    assert saved_output["lever"] == ["linear", "openai", "stripe"]

    saved_progress = json.loads(progress_path.read_text())
    assert saved_progress["metadata"]["status"] == "complete"
    assert saved_progress["metadata"]["completed_queries"] == 14
    assert saved_progress["metadata"]["total_queries"] is None
    assert len(saved_progress["exhausted_queries"]) == 6


@pytest.mark.asyncio
async def test_discover_companies_reuses_existing_registry_when_disabled(monkeypatch):
    config = SimpleNamespace(
        discovery=SimpleNamespace(
            enabled=False,
            timeout=5,
            searxng_url="http://192.168.0.5:8080/search",
            query_delay_seconds=0.0,
            max_pages=None,
        )
    )
    monkeypatch.setattr(company_discovery, "get_config", lambda: config)
    monkeypatch.setattr(
        "pipeline.sources.registry.get_all_slugs_by_ats",
        lambda: {"lever": ["stripe"], "greenhouse": ["databricks"], "ashby": []},
    )

    results = await company_discovery.discover_companies()

    assert results == {"lever": {"stripe"}, "greenhouse": {"databricks"}, "ashby": set()}


@pytest.mark.asyncio
async def test_search_searxng_accepts_base_or_search_endpoint():
    calls: list[tuple[str, dict[str, str | int]]] = []

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, list[dict[str, str]]]:
            return {"results": [{"url": "https://jobs.lever.co/stripe/123"}]}

    class _FakeClient:
        async def get(self, url: str, params: dict[str, str | int]):
            calls.append((url, params))
            return _FakeResponse()

    client = _FakeClient()

    urls_from_base = await company_discovery._search_searxng(
        client,
        "http://192.168.0.5:8080",
        "site:jobs.lever.co",
        page=1,
    )
    urls_from_search = await company_discovery._search_searxng(
        client,
        "http://192.168.0.5:8080/search",
        "site:jobs.lever.co",
        page=3,
    )

    assert urls_from_base == ["https://jobs.lever.co/stripe/123"]
    assert urls_from_search == ["https://jobs.lever.co/stripe/123"]
    assert calls[0] == ("http://192.168.0.5:8080/search", {"q": "site:jobs.lever.co", "format": "json", "pageno": 1})
    assert calls[1] == ("http://192.168.0.5:8080/search", {"q": "site:jobs.lever.co", "format": "json", "pageno": 3})
