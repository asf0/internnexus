from __future__ import annotations

import asyncio
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
    assert (
        company_discovery.extract_company_slug("https://job-boards.greenhouse.io/openai/jobs/456", "greenhouse")
        == "openai"
    )
    assert (
        company_discovery.extract_company_slug("https://boards.greenhouse.io/embed/job_board?for=spacex", "greenhouse")
        == "spacex"
    )
    assert (
        company_discovery.extract_company_slug(
            "https://boards.greenhouse.io/embed/job_board/js?for=journey", "greenhouse"
        )
        is None
    )
    assert company_discovery.extract_company_slug("https://jobs.ashbyhq.com/openai/abcd", "ashby") == "openai"
    assert company_discovery.extract_company_slug("https://example.com/openai/abcd", "ashby") is None


def test_build_search_queries_uses_site_country_and_apply_text():
    queries = company_discovery._build_search_queries(["United States"])

    assert ("global", "lever", 'site:jobs.lever.co intext:"apply"') in queries
    assert ("United States", "lever", 'site:jobs.lever.co United States intext:"apply"') in queries
    assert ("United States", "greenhouse", 'site:boards.greenhouse.io United States intext:"apply"') in queries
    assert ("United States", "ashby", 'site:jobs.ashbyhq.com United States intext:"apply"') in queries


@pytest.mark.asyncio
async def test_discover_companies_uses_searxng_results_and_persists(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "discovered_companies.json"
    progress_path = tmp_path / "discovery_progress.json"

    config = SimpleNamespace(
        discovery=SimpleNamespace(
            enabled=True,
            timeout=5,
            searxng_url="http://searxng:8080/search",
            query_delay_seconds=0.0,
            max_pages=None,
            countries=["United States"],
        )
    )
    monkeypatch.setattr(company_discovery, "get_config", lambda: config)

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
async def test_discover_companies_round_robins_pages_across_ats(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "discovered_companies.json"
    progress_path = tmp_path / "discovery_progress.json"

    config = SimpleNamespace(
        discovery=SimpleNamespace(
            enabled=True,
            timeout=5,
            searxng_url="http://searxng:8080/search",
            query_delay_seconds=0.0,
            max_pages=2,
            countries=[],
        )
    )
    monkeypatch.setattr(company_discovery, "get_config", lambda: config)

    calls: list[tuple[str, int]] = []

    async def _fake_search(_client, _base_url: str, query: str, *, page: int = 1) -> list[str]:
        calls.append((query, page))
        if "jobs.lever.co" in query:
            return [f"https://jobs.lever.co/lever{page}/job"]
        if "boards.greenhouse.io" in query:
            return [f"https://boards.greenhouse.io/greenhouse{page}/jobs/1"]
        if "jobs.ashbyhq.com" in query:
            return [f"https://jobs.ashbyhq.com/ashby{page}/job"]
        return []

    monkeypatch.setattr(company_discovery, "_search_searxng", _fake_search)

    await company_discovery.discover_companies(output_path=output_path, progress_path=progress_path)

    assert calls == [
        ('site:jobs.lever.co intext:"apply"', 1),
        ('site:boards.greenhouse.io intext:"apply"', 1),
        ('site:jobs.ashbyhq.com intext:"apply"', 1),
        ('site:jobs.lever.co intext:"apply"', 2),
        ('site:boards.greenhouse.io intext:"apply"', 2),
        ('site:jobs.ashbyhq.com intext:"apply"', 2),
    ]


@pytest.mark.asyncio
async def test_discover_companies_replaces_stale_output_after_complete_refresh(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "discovered_companies.json"
    progress_path = tmp_path / "discovery_progress.json"
    output_path.write_text(json.dumps({"lever": ["stale", "stripe"], "greenhouse": [], "ashby": []}))
    progress_path.write_text(
        json.dumps(
            {
                "metadata": {"status": "complete"},
                "completed_queries": ["global|lever|page:1"],
                "exhausted_queries": ["global|lever"],
                "companies": {"lever": ["stale"], "greenhouse": [], "ashby": []},
            }
        )
    )

    config = SimpleNamespace(
        discovery=SimpleNamespace(
            enabled=True,
            timeout=5,
            searxng_url="http://searxng:8080/search",
            query_delay_seconds=0.0,
            max_pages=None,
            countries=[],
        )
    )
    monkeypatch.setattr(company_discovery, "get_config", lambda: config)

    async def _fake_search(_client, _base_url: str, query: str, *, page: int = 1) -> list[str]:
        if "jobs.lever.co" in query and page == 1:
            return ["https://jobs.lever.co/stripe/123"]
        return []

    monkeypatch.setattr(company_discovery, "_search_searxng", _fake_search)

    results = await company_discovery.discover_companies(output_path=output_path, progress_path=progress_path)

    assert results["lever"] == {"stripe"}
    assert json.loads(output_path.read_text())["lever"] == ["stripe"]


@pytest.mark.asyncio
async def test_discover_companies_keeps_previous_output_when_complete_refresh_shrinks_too_much(
    monkeypatch, tmp_path: Path
):
    output_path = tmp_path / "discovered_companies.json"
    progress_path = tmp_path / "discovery_progress.json"
    previous = {
        "lever": [f"lever-{i}" for i in range(100)],
        "greenhouse": [f"greenhouse-{i}" for i in range(100)],
        "ashby": [f"ashby-{i}" for i in range(100)],
    }
    output_path.write_text(json.dumps(previous))

    config = SimpleNamespace(
        discovery=SimpleNamespace(
            enabled=True,
            timeout=5,
            searxng_url="http://searxng:8080/search",
            query_delay_seconds=0.0,
            max_pages=None,
            countries=[],
        )
    )
    monkeypatch.setattr(company_discovery, "get_config", lambda: config)

    async def _fake_search(_client, _base_url: str, query: str, *, page: int = 1) -> list[str]:
        if "jobs.lever.co" in query and page == 1:
            return ["https://jobs.lever.co/stripe/123"]
        return []

    results = await company_discovery.discover_companies(output_path=output_path, progress_path=progress_path)

    assert results["greenhouse"] == set(previous["greenhouse"])
    assert json.loads(output_path.read_text()) == previous


@pytest.mark.asyncio
async def test_discover_companies_keeps_previous_output_when_refresh_is_partial(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "discovered_companies.json"
    progress_path = tmp_path / "discovery_progress.json"
    previous = {"lever": ["stable"], "greenhouse": [], "ashby": []}
    output_path.write_text(json.dumps(previous))

    config = SimpleNamespace(
        discovery=SimpleNamespace(
            enabled=True,
            timeout=5,
            searxng_url="http://searxng:8080/search",
            query_delay_seconds=0.0,
            max_pages=None,
            countries=[],
        )
    )
    monkeypatch.setattr(company_discovery, "get_config", lambda: config)

    async def _fake_search(_client, _base_url: str, _query: str, *, page: int = 1) -> list[str]:
        if page == 1:
            raise RuntimeError("searxng down")
        return []

    monkeypatch.setattr(company_discovery, "_search_searxng", _fake_search)

    await company_discovery.discover_companies(output_path=output_path, progress_path=progress_path)

    assert json.loads(output_path.read_text()) == previous
    assert json.loads(progress_path.read_text())["metadata"]["status"] == "partial"


@pytest.mark.asyncio
async def test_discover_companies_merges_successes_when_refresh_is_partial(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "discovered_companies.json"
    progress_path = tmp_path / "discovery_progress.json"
    previous = {"lever": ["stable"], "greenhouse": [], "ashby": []}
    output_path.write_text(json.dumps(previous))

    config = SimpleNamespace(
        discovery=SimpleNamespace(
            enabled=True,
            timeout=5,
            searxng_url="http://searxng:8080/search",
            query_delay_seconds=0.0,
            max_pages=None,
            countries=[],
        )
    )
    monkeypatch.setattr(company_discovery, "get_config", lambda: config)

    async def _fake_search(_client, _base_url: str, query: str, *, page: int = 1) -> list[str]:
        if "jobs.lever.co" in query and page == 1:
            return ["https://jobs.lever.co/stripe/123"]
        if "boards.greenhouse.io" in query and page == 1:
            raise RuntimeError("searxng rate limited")
        return []

    monkeypatch.setattr(company_discovery, "_search_searxng", _fake_search)

    results = await company_discovery.discover_companies(output_path=output_path, progress_path=progress_path)

    assert results["lever"] == {"stable", "stripe"}
    assert json.loads(output_path.read_text())["lever"] == ["stable", "stripe"]
    assert json.loads(progress_path.read_text())["metadata"]["status"] == "partial"


@pytest.mark.asyncio
async def test_discover_companies_tries_all_queries_on_searxng_failure(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "discovered_companies.json"
    progress_path = tmp_path / "discovery_progress.json"
    output_path.write_text(json.dumps({"lever": ["stable"], "greenhouse": [], "ashby": []}))

    config = SimpleNamespace(
        discovery=SimpleNamespace(
            enabled=True,
            timeout=5,
            searxng_url="http://searxng:8080/search",
            query_delay_seconds=0.0,
            max_pages=None,
            countries=["United States"],
        )
    )
    monkeypatch.setattr(company_discovery, "get_config", lambda: config)

    calls = 0

    async def _fake_search(_client, _base_url: str, _query: str, *, page: int = 1) -> list[str]:
        nonlocal calls
        calls += 1
        raise RuntimeError("SearxNG returned no URLs with unresponsive engines")

    monkeypatch.setattr(company_discovery, "_search_searxng", _fake_search)

    results = await company_discovery.discover_companies(output_path=output_path, progress_path=progress_path)

    # A single failed query no longer aborts discovery; all page-1 queries are
    # attempted before the "no progress" guard stops the run.
    assert calls == 6
    assert results["lever"] == {"stable"}
    assert json.loads(progress_path.read_text())["metadata"]["status"] == "partial"


@pytest.mark.asyncio
async def test_discover_companies_reuses_existing_registry_when_disabled(monkeypatch):
    config = SimpleNamespace(
        discovery=SimpleNamespace(
            enabled=False,
            timeout=5,
            searxng_url="http://searxng:8080/search",
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
        "http://searxng:8080",
        "site:jobs.lever.co",
        page=1,
    )
    urls_from_search = await company_discovery._search_searxng(
        client,
        "http://searxng:8080/search",
        "site:jobs.lever.co",
        page=3,
    )

    assert urls_from_base == ["https://jobs.lever.co/stripe/123"]
    assert urls_from_search == ["https://jobs.lever.co/stripe/123"]
    assert calls[0] == ("http://searxng:8080/search", {"q": "site:jobs.lever.co", "format": "json", "pageno": 1})
    assert calls[1] == ("http://searxng:8080/search", {"q": "site:jobs.lever.co", "format": "json", "pageno": 3})


@pytest.mark.asyncio
async def test_search_searxng_treats_empty_unresponsive_engines_as_failure():
    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, list]:
            return {"results": [], "unresponsive_engines": [["brave", "too many requests"]]}

    class _FakeClient:
        async def get(self, _url: str, params: dict[str, str | int]):
            return _FakeResponse()

    with pytest.raises(RuntimeError, match="unresponsive engines"):
        await company_discovery._search_searxng(
            _FakeClient(),
            "http://searxng:8080/search",
            "site:jobs.ashbyhq.com",
            page=1,
        )


# -- Extracted helper tests --


def test_determine_run_status_partial_on_failure():
    assert (
        company_discovery._determine_run_status(
            any_query_failed=True,
            all_exhausted=True,
            reached_page_cap=True,
        )
        == "partial"
    )
    assert (
        company_discovery._determine_run_status(
            any_query_failed=True,
            all_exhausted=False,
            reached_page_cap=False,
        )
        == "partial"
    )


def test_determine_run_status_complete_when_exhausted():
    assert (
        company_discovery._determine_run_status(
            any_query_failed=False,
            all_exhausted=True,
            reached_page_cap=False,
        )
        == "complete"
    )


def test_determine_run_status_capped_when_not_exhausted():
    assert (
        company_discovery._determine_run_status(
            any_query_failed=False,
            all_exhausted=False,
            reached_page_cap=True,
        )
        == "capped"
    )


def test_finalize_discovery_output_saves_new_on_complete(tmp_path: Path):
    output_path = tmp_path / "companies.json"
    progress = {
        "metadata": {"status": "complete"},
        "companies": {"lever": ["stripe"], "greenhouse": [], "ashby": []},
    }

    company_discovery._finalize_discovery_output(progress, "complete", output_path)

    assert output_path.exists()
    assert json.loads(output_path.read_text()) == {"lever": ["stripe"], "greenhouse": [], "ashby": []}


def test_finalize_discovery_output_keeps_previous_on_shrink(tmp_path: Path):
    output_path = tmp_path / "companies.json"
    previous = {
        "lever": [f"lever-{i}" for i in range(100)],
        "greenhouse": [f"greenhouse-{i}" for i in range(100)],
        "ashby": [f"ashby-{i}" for i in range(100)],
    }
    output_path.write_text(json.dumps(previous))

    progress = {
        "metadata": {"status": "complete"},
        "companies": {"lever": ["stripe"], "greenhouse": [], "ashby": []},
    }

    result = company_discovery._finalize_discovery_output(progress, "complete", output_path)

    assert result["greenhouse"] == set(previous["greenhouse"])
    assert json.loads(output_path.read_text()) == previous


def test_finalize_discovery_output_merges_on_partial(tmp_path: Path):
    output_path = tmp_path / "companies.json"
    previous = {"lever": ["stable"], "greenhouse": [], "ashby": []}
    output_path.write_text(json.dumps(previous))

    progress = {
        "metadata": {"status": "partial"},
        "companies": {"lever": ["stripe"], "greenhouse": [], "ashby": []},
    }

    result = company_discovery._finalize_discovery_output(progress, "partial", output_path)

    assert result["lever"] == {"stable", "stripe"}
    assert json.loads(output_path.read_text())["lever"] == ["stable", "stripe"]


@pytest.mark.asyncio
async def test_run_one_query_updates_progress_on_success(monkeypatch, tmp_path: Path):
    progress_path = tmp_path / "progress.json"
    progress = company_discovery._default_progress()
    completed: set[str] = set()
    exhausted: set[str] = set()

    async def _fake_search(_client, _base_url, _query, *, page=1):
        return ["https://jobs.lever.co/stripe/123"]

    monkeypatch.setattr(company_discovery, "_search_searxng", _fake_search)

    advanced = await company_discovery._run_one_query(
        None,
        "http://searxng:8080",
        "global",
        "lever",
        "site:jobs.lever.co",
        1,
        1,
        1,
        progress,
        progress_path,
        completed,
        exhausted,
        0.0,
    )

    assert advanced is True
    assert "global|lever|page:1" in completed
    assert "stripe" in progress["companies"]["lever"]


@pytest.mark.asyncio
async def test_run_one_query_marks_exhausted_on_empty(monkeypatch, tmp_path: Path):
    progress_path = tmp_path / "progress.json"
    progress = company_discovery._default_progress()
    completed: set[str] = set()
    exhausted: set[str] = set()

    async def _fake_search(_client, _base_url, _query, *, page=1):
        return []

    monkeypatch.setattr(company_discovery, "_search_searxng", _fake_search)

    advanced = await company_discovery._run_one_query(
        None,
        "http://searxng:8080",
        "global",
        "lever",
        "site:jobs.lever.co",
        1,
        1,
        1,
        progress,
        progress_path,
        completed,
        exhausted,
        0.0,
    )

    assert advanced is True
    assert "global|lever" in exhausted
    assert "global|lever|page:1" in completed


@pytest.mark.asyncio
async def test_run_one_query_propagates_exception(monkeypatch, tmp_path: Path):
    progress_path = tmp_path / "progress.json"
    progress = company_discovery._default_progress()
    completed: set[str] = set()
    exhausted: set[str] = set()

    async def _fake_search(_client, _base_url, _query, *, page=1):
        raise RuntimeError("network error")

    monkeypatch.setattr(company_discovery, "_search_searxng", _fake_search)

    with pytest.raises(RuntimeError, match="network error"):
        await company_discovery._run_one_query(
            None,
            "http://searxng:8080",
            "global",
            "lever",
            "site:jobs.lever.co",
            1,
            1,
            1,
            progress,
            progress_path,
            completed,
            exhausted,
            0.0,
        )

    assert completed == set()
    assert exhausted == set()


@pytest.mark.asyncio
async def test_run_one_query_skips_already_exhausted():
    progress = company_discovery._default_progress()
    completed: set[str] = set()
    exhausted: set[str] = {"global|lever"}

    advanced = await company_discovery._run_one_query(
        None,
        "http://searxng:8080",
        "global",
        "lever",
        "site:jobs.lever.co",
        1,
        1,
        1,
        progress,
        Path("/dev/null"),
        completed,
        exhausted,
        0.0,
    )

    assert advanced is False


@pytest.mark.asyncio
async def test_run_one_query_skips_already_completed():
    progress = company_discovery._default_progress()
    completed: set[str] = {"global|lever|page:1"}
    exhausted: set[str] = set()

    advanced = await company_discovery._run_one_query(
        None,
        "http://searxng:8080",
        "global",
        "lever",
        "site:jobs.lever.co",
        1,
        1,
        1,
        progress,
        Path("/dev/null"),
        completed,
        exhausted,
        0.0,
    )

    assert advanced is True


@pytest.mark.asyncio
async def test_iter_queries_until_exhausted_returns_crawl_result(monkeypatch, tmp_path: Path):
    progress_path = tmp_path / "progress.json"
    progress = company_discovery._default_progress()
    completed: set[str] = set()
    exhausted: set[str] = set()
    queries = [("global", "lever", 'site:jobs.lever.co intext:"apply"')]

    call_count = 0

    async def _fake_search(_client, _base_url, _query, *, page=1):
        nonlocal call_count
        call_count += 1
        if page == 1:
            return ["https://jobs.lever.co/stripe/123"]
        return []

    monkeypatch.setattr(company_discovery, "_search_searxng", _fake_search)

    class _FakeClient:
        pass

    result = await company_discovery._iter_queries_until_exhausted(
        queries,
        progress,
        progress_path,
        completed,
        exhausted,
        None,
        _FakeClient(),
        "http://searxng:8080",
        0.0,
    )

    assert isinstance(result, company_discovery.CrawlResult)
    assert result.any_query_failed is False
    assert result.all_exhausted is True
    assert result.reached_page_cap is False
    assert call_count == 2  # page 1 (results), page 2 (empty -> exhausted)


@pytest.mark.asyncio
async def test_iter_queries_stops_when_only_remaining_query_fails(monkeypatch, tmp_path: Path):
    """An exhausted query must not keep an uncapped failed crawl alive."""
    calls: list[tuple[str, int]] = []

    async def _fake_search(_client, _base_url, query, *, page=1):
        calls.append((query, page))
        if query == "exhausts":
            return []
        raise RuntimeError("network error")

    monkeypatch.setattr(company_discovery, "_search_searxng", _fake_search)

    result = await asyncio.wait_for(
        company_discovery._iter_queries_until_exhausted(
            [
                ("global", "lever", "exhausts"),
                ("global", "ashby", "fails"),
            ],
            company_discovery._default_progress(),
            tmp_path / "progress.json",
            set(),
            set(),
            None,
            object(),
            "http://searxng:8080",
            0.0,
        ),
        timeout=0.5,
    )

    assert calls == [
        ("exhausts", 1),
        ("fails", 1),
        ("fails", 2),
    ]
    assert result.any_query_failed is True
    assert result.all_exhausted is False
    assert result.reached_page_cap is False


def test_discover_companies_uses_configured_countries(monkeypatch, tmp_path: Path):
    """Verify that config.discovery.countries flows through to query building."""
    output_path = tmp_path / "discovered_companies.json"
    progress_path = tmp_path / "discovery_progress.json"

    config = SimpleNamespace(
        discovery=SimpleNamespace(
            enabled=True,
            timeout=5,
            searxng_url="http://searxng:8080/search",
            query_delay_seconds=0.0,
            max_pages=None,
            countries=["Brazil"],
        )
    )
    monkeypatch.setattr(company_discovery, "get_config", lambda: config)

    captured_queries: list[str] = []

    async def _fake_search(_client, _base_url: str, query: str, *, page: int = 1) -> list[str]:
        captured_queries.append(query)
        return []

    monkeypatch.setattr(company_discovery, "_search_searxng", _fake_search)

    import asyncio

    asyncio.run(company_discovery.discover_companies(output_path=output_path, progress_path=progress_path))

    # _build_search_queries emits global queries (no country) + country-scoped queries
    # Verify Brazil appears in country-scoped queries
    brazil_queries = [q for q in captured_queries if "Brazil" in q]
    assert len(brazil_queries) == 3  # one per ATS
    # Verify no other default countries appear
    for query in captured_queries:
        assert "United States" not in query
        assert "Korea" not in query
        assert "Ireland" not in query
        assert "Canada" not in query
        assert "United Kingdom" not in query
        assert "Germany" not in query
