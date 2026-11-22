from __future__ import annotations

from pipeline.tests.paths import PROJECT_ROOT
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.cli import consolidate_categories as cc


# ---------------------------------------------------------------------------
# _parse_args
# ---------------------------------------------------------------------------


def test_parse_args_defaults():
    ns = cc._parse_args([])
    assert ns.dry_run is False
    assert ns.stats is False
    assert ns.list_canonical is False
    assert ns.batch_size == 1000


def test_parse_args_dry_run():
    ns = cc._parse_args(["--dry-run"])
    assert ns.dry_run is True


def test_parse_args_stats():
    ns = cc._parse_args(["--stats"])
    assert ns.stats is True


def test_parse_args_list_canonical():
    ns = cc._parse_args(["--list-canonical"])
    assert ns.list_canonical is True


def test_parse_args_batch_size():
    ns = cc._parse_args(["--batch-size", "500"])
    assert ns.batch_size == 500


def test_parse_args_stats_with_batch_size():
    ns = cc._parse_args(["--stats", "--batch-size", "500"])
    assert ns.stats is True
    assert ns.batch_size == 500


def test_parse_args_dry_run_with_batch_size():
    ns = cc._parse_args(["--dry-run", "--batch-size", "200"])
    assert ns.dry_run is True
    assert ns.batch_size == 200


# ---------------------------------------------------------------------------
# _print_stats_mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_print_stats_mode(monkeypatch, capsys):
    fake_session = AsyncMock()
    monkeypatch.setattr(cc, "get_category_stats", AsyncMock(return_value={"eng": 10, "mkt": 5}))
    monkeypatch.setattr(cc, "get_total_jobs", AsyncMock(return_value=100))
    monkeypatch.setattr(cc, "get_null_count", AsyncMock(return_value=85))

    result = await cc._print_stats_mode(fake_session)

    assert result == 0
    captured = capsys.readouterr().out
    assert "CURRENT CATEGORY STATISTICS" in captured
    assert "Total jobs: 100" in captured
    assert "Jobs with NULL category: 85" in captured
    assert "Jobs with category: 15" in captured
    assert "Unique categories: 2" in captured
    assert "eng" in captured
    assert "mkt" in captured


# ---------------------------------------------------------------------------
# _print_apply_result
# ---------------------------------------------------------------------------


def test_print_apply_result_with_updated_counts(capsys):
    result = {
        "nullified": 5,
        "categories_before": 42,
        "categories_after": 27,
        "updated_counts": {"software_engineering": 100, "data_science": 50},
    }
    cc._print_apply_result(result)
    captured = capsys.readouterr().out
    assert "CONSOLIDATION COMPLETE" in captured
    assert "Jobs nullified: 5" in captured
    assert "Categories before: 42" in captured
    assert "Categories after: 27" in captured
    assert "software_engineering" in captured
    assert "data_science" in captured
    assert "Jobs per canonical category:" in captured


def test_print_apply_result_without_updated_counts(capsys):
    result = {
        "nullified": 0,
        "categories_before": 10,
        "categories_after": 10,
        "updated_counts": {},
    }
    cc._print_apply_result(result)
    captured = capsys.readouterr().out
    assert "Jobs nullified: 0" in captured
    assert "Categories before: 10" in captured
    assert "Categories after: 10" in captured
    assert "Jobs per canonical category:" not in captured


# ---------------------------------------------------------------------------
# _run_consolidation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_consolidation_dry_run(monkeypatch):
    fake_session = AsyncMock()
    fake_analysis = {"total_jobs": 100, "current_nulls": 0, "total_categories_before": 10}

    monkeypatch.setattr(cc, "analyze_consolidation", AsyncMock(return_value=fake_analysis))
    monkeypatch.setattr(cc, "print_analysis", lambda _: None)
    monkeypatch.setattr(cc, "apply_consolidation", AsyncMock())
    monkeypatch.setattr(cc, "_print_apply_result", lambda _: None)

    result = await cc._run_consolidation(fake_session, dry_run=True, batch_size=500)

    assert result == 0
    cc.analyze_consolidation.assert_awaited_once_with(fake_session)
    cc.apply_consolidation.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_consolidation_declined(monkeypatch):
    fake_session = AsyncMock()
    fake_analysis = {"total_jobs": 100, "current_nulls": 0}

    monkeypatch.setattr(cc, "analyze_consolidation", AsyncMock(return_value=fake_analysis))
    monkeypatch.setattr(cc, "print_analysis", lambda _: None)
    monkeypatch.setattr(cc, "apply_consolidation", AsyncMock())
    monkeypatch.setattr(cc, "_print_apply_result", lambda _: None)
    monkeypatch.setattr("asyncio.to_thread", AsyncMock(return_value="n"))

    result = await cc._run_consolidation(fake_session, dry_run=False, batch_size=1000)

    assert result == 1
    cc.apply_consolidation.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_consolidation_confirmed(monkeypatch):
    fake_session = AsyncMock()
    fake_analysis = {"total_jobs": 100, "current_nulls": 0}
    fake_result = {"nullified": 5, "categories_before": 42, "categories_after": 27, "updated_counts": {}}

    monkeypatch.setattr(cc, "analyze_consolidation", AsyncMock(return_value=fake_analysis))
    monkeypatch.setattr(cc, "print_analysis", lambda _: None)
    monkeypatch.setattr(cc, "apply_consolidation", AsyncMock(return_value=fake_result))
    monkeypatch.setattr(cc, "_print_apply_result", lambda _: None)
    monkeypatch.setattr("asyncio.to_thread", AsyncMock(return_value="y"))

    result = await cc._run_consolidation(fake_session, dry_run=False, batch_size=200)

    assert result == 0
    cc.analyze_consolidation.assert_awaited_once_with(fake_session)
    cc.apply_consolidation.assert_awaited_once_with(fake_session, batch_size=200)


@pytest.mark.asyncio
async def test_run_consolidation_batch_size_forwarded(monkeypatch):
    fake_session = AsyncMock()
    fake_analysis = {"total_jobs": 100, "current_nulls": 0}

    monkeypatch.setattr(cc, "analyze_consolidation", AsyncMock(return_value=fake_analysis))
    monkeypatch.setattr(cc, "print_analysis", lambda _: None)
    monkeypatch.setattr(cc, "apply_consolidation", AsyncMock(return_value={}))
    monkeypatch.setattr(cc, "_print_apply_result", lambda _: None)
    monkeypatch.setattr("asyncio.to_thread", AsyncMock(return_value="y"))

    await cc._run_consolidation(fake_session, dry_run=False, batch_size=777)
    cc.apply_consolidation.assert_awaited_once_with(fake_session, batch_size=777)


# ---------------------------------------------------------------------------
# main() routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_main_list_canonical(monkeypatch):
    monkeypatch.setattr(
        cc,
        "_parse_args",
        lambda argv: type(
            "Args",
            (),
            {
                "list_canonical": True,
                "stats": False,
                "dry_run": False,
                "batch_size": 1000,
            },
        )(),
    )
    calls = []
    monkeypatch.setattr(cc, "print_canonical_categories", lambda: calls.append("printed"))

    result = await cc.main(argv=[])

    assert result == 0
    assert calls == ["printed"]


@pytest.mark.asyncio
async def test_main_stats_mode(monkeypatch):
    monkeypatch.setattr(
        cc,
        "_parse_args",
        lambda argv: type(
            "Args",
            (),
            {
                "list_canonical": False,
                "stats": True,
                "dry_run": False,
                "batch_size": 1000,
            },
        )(),
    )

    async def fake_print_stats(_session):
        return 42

    monkeypatch.setattr(cc, "_print_stats_mode", fake_print_stats)
    monkeypatch.setattr(cc, "AsyncSessionLocal", lambda: AsyncMock())

    result = await cc.main(argv=[])
    assert result == 42


@pytest.mark.asyncio
async def test_main_consolidation(monkeypatch):
    monkeypatch.setattr(
        cc,
        "_parse_args",
        lambda argv: type(
            "Args",
            (),
            {
                "list_canonical": False,
                "stats": False,
                "dry_run": True,
                "batch_size": 500,
                "yes": False,
            },
        )(),
    )

    async def fake_run_consolidation(_session, *, dry_run, batch_size, assume_yes):
        assert dry_run is True
        assert batch_size == 500
        assert assume_yes is False
        return 0

    monkeypatch.setattr(cc, "_run_consolidation", fake_run_consolidation)
    monkeypatch.setattr(cc, "AsyncSessionLocal", lambda: AsyncMock())

    result = await cc.main(argv=[])
    assert result == 0


@pytest.mark.asyncio
async def test_main_list_canonical_does_not_open_db_session(monkeypatch):
    monkeypatch.setattr(
        cc,
        "_parse_args",
        lambda argv: type(
            "Args",
            (),
            {
                "list_canonical": True,
                "stats": False,
                "dry_run": False,
                "batch_size": 1000,
            },
        )(),
    )
    monkeypatch.setattr(cc, "print_canonical_categories", lambda: None)

    def fail_session():
        raise AssertionError("should not open DB session for --list-canonical")

    monkeypatch.setattr(cc, "AsyncSessionLocal", fail_session)

    result = await cc.main(argv=[])
    assert result == 0
