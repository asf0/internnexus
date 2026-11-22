"""Golden fixture tests for cleanup loops.

Captures current behavior of:
- _parse_location_only over 15 representative location strings
- _process_production_mode_chunked over 10 job sets
- _process_test_mode_chunked over 10 job sets with CSV byte comparison
- _normalize_existing_states over 5 representative rows
"""

from __future__ import annotations

from pipeline.tests.paths import FIXTURES_DIR
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import pytest

from pipeline.stages.cleanup import batch_updater as bp
from pipeline.stages.cleanup import exporter as ex_mod
from pipeline.stages.cleanup import normalizer as norm_mod
from pipeline.stages.cleanup import location_parser as parser_mod
from pipeline.stages.cleanup.location_parser import _parse_location_only
from pipeline.stages.cleanup.location.cache import ParsedLocation
from pipeline.repositories import LocationUpdate
from pipeline.stages.cleanup.location.constants import (
    COUNTRIES_AS_STATES as _COUNTRIES_AS_STATES,
    STATE_MAPPINGS as _STATE_MAPPINGS,
)

# Statement counts the fake normalizer session uses to route calls. Derived from
# the constants so the routing follows the normalizer automatically. Identity
# mappings are excluded because the normalizer skips them.
_N_COUNTRIES_AS_STATES = len(_COUNTRIES_AS_STATES)
_N_REMAP = len([k for k, v in _STATE_MAPPINGS.items() if v is not None and k != v])

# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

_FIXTURE_PATH = FIXTURES_DIR / "cleanup_golden_cases.json"


def _load_fixture():
    with open(_FIXTURE_PATH) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_job(entry):
    return SimpleNamespace(
        id=UUID(entry["id"]),
        source=entry.get("source", ""),
        location=entry.get("location"),
        city=entry.get("city"),
        state=entry.get("state"),
        country=entry.get("country"),
    )


def _setup_fake_cache(monkeypatch):
    cache = _FakeCache()
    monkeypatch.setattr(parser_mod, "get_location_cache", Mock(return_value=cache))
    return cache


class _FakeCache:
    """In-memory cache that stores real ParsedLocation objects."""

    def __init__(self):
        self._store: dict[str, ParsedLocation] = {}

    def get(self, location: str) -> ParsedLocation | None:
        return self._store.get(location)

    def set(self, location: str, result: ParsedLocation) -> None:
        self._store[location] = result

    def preload(self, location: str, result: ParsedLocation) -> None:
        self._store[location] = result


# ---------------------------------------------------------------------------
# FakeJobRepo — compatible constructor __init__(self, session)
# ---------------------------------------------------------------------------


class _FakeJobRepo:
    def __init__(self, session):
        self._session = session
        self._jobs: list = []
        self._total_count = 0
        self._max_page_size = 0
        self.captured_updates: list[list[LocationUpdate]] = []
        self.pagination_calls: list[dict] = []

    def load(self, jobs, total_count, max_page_size=0):
        self._jobs = list(jobs)
        self._total_count = total_count
        self._max_page_size = max_page_size

    async def get_total_count(self, since, process_all):
        return self._total_count

    async def fetch_jobs_batch_keyset(self, since, process_all, last_id, limit):
        remaining = sorted(self._jobs, key=lambda j: j.id)
        if last_id is not None:
            remaining = [j for j in remaining if j.id > last_id]
        effective = min(limit, self._max_page_size) if self._max_page_size else limit
        batch = remaining[:effective]
        self.pagination_calls.append(
            {
                "last_id": str(last_id) if last_id is not None else None,
                "limit": limit,
                "returned_count": len(batch),
                "returned_ids": [str(j.id) for j in batch],
            }
        )
        return list(batch)

    async def update_job_locations(self, updates):
        self.captured_updates.append(list(updates))
        for upd in updates:
            for job in self._jobs:
                if job.id == upd.job_id:
                    job.city = upd.city
                    job.state = upd.state
                    job.country = upd.country
                    break
        return len(updates)


# ---------------------------------------------------------------------------
# FakeNormalizerSession
# ---------------------------------------------------------------------------


class _FakeNormalizerSession:
    def __init__(self, initial_rows):
        self._rows = [dict(r) for r in initial_rows]
        self.call_index = 0
        self.executed_calls: list[dict] = []
        self.commits = 0

    def _current_rows(self):
        return [dict(r) for r in self._rows]

    def _apply_trim(self, col):
        affected = 0
        for row in self._rows:
            val = row.get(col)
            if val and val != val.strip():
                row[col] = val.strip()
                affected += 1
        return affected

    # Param names below follow SQLAlchemy Core compilation of the update()
    # constructs in pipeline.stages.cleanup.normalizer: SET values keep the column
    # name ('state', 'city', 'country'), the WHERE comparison value becomes
    # 'state_1'/'city_1', and lowered IN lists become 'lower_1'.

    def _apply_set_country_null_state(self, params):
        state_val = params["state_1"]
        country_val = params["country"]
        affected = 0
        for row in self._rows:
            if row.get("state") == state_val:
                row["country"] = country_val
                row["state"] = None
                affected += 1
        return affected

    def _apply_null_state_any(self, params):
        values = set(params["state_1"])
        affected = 0
        for row in self._rows:
            if row.get("state") in values:
                row["state"] = None
                affected += 1
        return affected

    def _apply_remap_state(self, params):
        old = params["state_1"]
        new = params["state"]
        affected = 0
        for row in self._rows:
            if row.get("state") == old:
                row["state"] = new
                affected += 1
        return affected

    def _apply_null_city_any(self, params):
        values_lower = {v.lower() for v in params["lower_1"]}
        affected = 0
        for row in self._rows:
            city = row.get("city")
            if city and city.lower() in values_lower:
                row["city"] = None
                affected += 1
        return affected

    def _apply_null_city_regex(self, params):
        import re

        pattern = params["city_1"]
        compiled = re.compile(pattern, re.IGNORECASE)
        affected = 0
        for row in self._rows:
            city = row.get("city")
            if city and compiled.search(city):
                row["city"] = None
                affected += 1
        return affected

    async def execute(self, statement, parameters=None):
        sql_text = str(statement)
        params = parameters or dict(statement.compile().params)
        idx = self.call_index
        # Boundaries are derived from the same constants the normalizer reads
        # rather than hardcoded, so adding or removing a mapping cannot silently
        # misroute statements here. `_N_REMAP` excludes identity mappings, which
        # the normalizer deliberately skips (they would rewrite a row to the
        # value it already holds).
        n_trim = 3
        n_country = n_trim + _N_COUNTRIES_AS_STATES
        n_null_state = n_country + 2
        n_remap = n_null_state + _N_REMAP
        affected = 0
        if idx < n_trim:
            cols = ["state", "city", "country"]
            affected = self._apply_trim(cols[idx])
        elif idx < n_country:
            affected = self._apply_set_country_null_state(params)
        elif idx < n_null_state:
            affected = self._apply_null_state_any(params)
        elif idx < n_remap:
            affected = self._apply_remap_state(params)
        elif idx == n_remap:
            affected = self._apply_null_state_any(params)
        elif idx == n_remap + 1:
            affected = self._apply_null_city_any(params)
        elif idx == n_remap + 2:
            affected = self._apply_null_city_any(params)
        elif idx == n_remap + 3:
            affected = self._apply_null_city_regex(params)
        self.executed_calls.append({"index": idx, "sql": sql_text, "params": params, "affected": affected})
        self.call_index += 1
        return SimpleNamespace(rowcount=affected)

    async def commit(self):
        self.commits += 1


# ============================================================================
# Section A — Parser golden tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("case", _load_fixture()["parser_cases"], ids=lambda c: c["name"])
async def test_parser_golden(case, monkeypatch):
    cache = _setup_fake_cache(monkeypatch)
    if "preload" in case:
        for loc, fields in case["preload"].items():
            cache.preload(
                loc,
                ParsedLocation(
                    city=fields.get("city"),
                    state=fields.get("state"),
                    country=fields.get("country"),
                ),
            )
    result = _parse_location_only(case["input"])
    expected = case["expected"]
    assert result["city"] == expected["city"], f"{case['name']}: city mismatch"
    assert result["state"] == expected["state"], f"{case['name']}: state mismatch"
    assert result["country"] == expected["country"], f"{case['name']}: country mismatch"


# ============================================================================
# Section B — Production loop golden tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("case", _load_fixture()["production_cases"], ids=lambda c: c["name"])
async def test_production_golden(case, monkeypatch):
    _setup_fake_cache(monkeypatch)

    params = case["params"]
    jobs = [_make_job(e) for e in params["jobs"]]
    total_count = params["total_count"]
    limit = params.get("limit")
    chunk_size = params.get("chunk_size", 5000)
    location_cache_max_size = params.get("location_cache_max_size", 10_000)

    repo = _FakeJobRepo(session=None)
    repo.load(jobs, total_count)

    monkeypatch.setattr(bp, "SQLAlchemyJobRepository", lambda _s: repo)
    fake_session = SimpleNamespace(expunge_all=lambda: None)

    updated = await bp._process_production_mode_chunked(
        fake_session,  # pyright: ignore[reportArgumentType]
        since=None,
        process_all=True,
        limit=limit,
        parse_concurrency=2,
        chunk_size=chunk_size,
        location_cache_max_size=location_cache_max_size,
    )

    expected = case["expected"]
    assert updated == expected["updated"], f"{case['name']}: updated mismatch"

    # Snapshot: every job must have an expected entry
    expected_snapshot = expected["snapshot"]
    for job in repo._jobs:
        jid = str(job.id)
        exp = expected_snapshot.get(jid)
        assert exp is not None, f"{case['name']}: no expected snapshot for job {jid}"
        assert job.city == exp.get("city"), f"{case['name']}: city mismatch for {jid}"
        assert job.state == exp.get("state"), f"{case['name']}: state mismatch for {jid}"
        assert job.country == exp.get("country"), f"{case['name']}: country mismatch for {jid}"
    assert len(repo._jobs) == len(expected_snapshot), f"{case['name']}: job count mismatch"

    # Pagination calls
    if "expected_pagination_calls" in expected:
        _assert_pagination(repo.pagination_calls, expected["expected_pagination_calls"], case["name"])

    # Update batches: assert exact job IDs
    if "expected_update_batches" in expected:
        exp_batches = expected["expected_update_batches"]
        assert len(repo.captured_updates) == len(exp_batches), (
            f"{case['name']}: batch count mismatch {len(repo.captured_updates)} vs {len(exp_batches)}"
        )
        for bi, (actual_updates, exp_ids) in enumerate(zip(repo.captured_updates, exp_batches)):
            actual_ids = [str(u.job_id) for u in actual_updates]
            assert actual_ids == exp_ids, f"{case['name']}: batch [{bi}] IDs mismatch"


def _assert_pagination(actual_calls, expected_calls, case_name):
    assert len(actual_calls) == len(expected_calls), (
        f"{case_name}: pagination call count mismatch {len(actual_calls)} vs {len(expected_calls)}"
    )
    for i, (act, exp) in enumerate(zip(actual_calls, expected_calls)):
        assert act["last_id"] == exp["last_id"], f"{case_name}: page [{i}] last_id mismatch"
        assert act["limit"] == exp["limit"], f"{case_name}: page [{i}] limit mismatch"
        assert act["returned_count"] == exp["returned_count"], f"{case_name}: page [{i}] returned_count mismatch"
        assert act["returned_ids"] == exp["returned_ids"], f"{case_name}: page [{i}] returned_ids mismatch"


# ============================================================================
# Section C — Test mode loop golden tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("case", _load_fixture()["test_mode_cases"], ids=lambda c: c["name"])
async def test_testmode_golden(case, monkeypatch, tmp_path):
    _setup_fake_cache(monkeypatch)

    params = case["params"]
    jobs = [_make_job(e) for e in params["jobs"]]
    total_count = params["total_count"]
    limit = params.get("limit")
    max_page_size = params.get("max_page_size", 0)

    repo = _FakeJobRepo(session=None)
    repo.load(jobs, total_count, max_page_size=max_page_size)

    monkeypatch.setattr(ex_mod, "SQLAlchemyJobRepository", lambda _s: repo)
    output_dir = tmp_path / "output"
    monkeypatch.setattr(ex_mod, "OUTPUT_DIR", output_dir)

    result = await ex_mod._process_test_mode_chunked(
        SimpleNamespace(),  # pyright: ignore[reportArgumentType]
        since=None,
        process_all=True,
        limit=limit,
        location_cache_max_size=10_000,
    )

    expected = case["expected"]
    assert result == expected["processed"], f"{case['name']}: processed mismatch"

    csv_path = output_dir / "location_test_results.csv"
    actual_bytes = csv_path.read_bytes()
    expected_bytes = expected["csv"].encode("utf-8")
    assert actual_bytes == expected_bytes, f"{case['name']}: CSV mismatch"

    # Pagination calls for multi-chunk cases
    if "expected_pagination_calls" in expected:
        _assert_pagination(repo.pagination_calls, expected["expected_pagination_calls"], case["name"])


# ============================================================================
# Section D — State normalizer golden tests
# ============================================================================


def test_normalizer_golden():
    from pipeline.stages.cleanup.location.constants import (
        CITIES_AS_STATES,
        COUNTRIES_AS_CITIES,
        COUNTRIES_AS_STATES,
        INVALID_CITY_PATTERN_STRINGS,
        INVALID_STATES,
        STATE_MAPPINGS,
        STATES_AS_CITIES,
    )

    fixture = _load_fixture()["normalizer_cases"]
    rows = [dict(r) for r in fixture["initial_rows"]]
    expected_rows = [dict(r) for r in fixture["expected_rows"]]

    session = _FakeNormalizerSession(rows)
    total = asyncio.run(norm_mod._normalize_existing_states(session))  # pyright: ignore[reportArgumentType]

    assert session.commits == 1
    # 3 trims + 64 country-as-state + 2 null-state + non-identity remaps
    # + 1 null-state + 2 city-list + 1 city-regex.
    assert session.call_index == 3 + _N_COUNTRIES_AS_STATES + 2 + _N_REMAP + 4
    assert total == sum(c["affected"] for c in session.executed_calls)
    assert total == fixture["expected_total"]

    # Build expected call list independently from the same constants
    expected_calls = _build_normalizer_expected_calls(
        COUNTRIES_AS_STATES,
        CITIES_AS_STATES,
        INVALID_STATES,
        STATE_MAPPINGS,
        COUNTRIES_AS_CITIES,
        STATES_AS_CITIES,
        INVALID_CITY_PATTERN_STRINGS,
    )

    expected_count = 3 + _N_COUNTRIES_AS_STATES + 2 + _N_REMAP + 4
    assert len(expected_calls) == expected_count, (
        f"Expected {expected_count} calls, built {len(expected_calls)}"
    )
    for i in range(expected_count):
        act = session.executed_calls[i]
        exp = expected_calls[i]
        assert act["sql"] == exp["sql"], f"Call [{i}]: SQL mismatch\ngot  {act['sql']!r}\nexp  {exp['sql']!r}"
        assert act["params"] == exp["params"], (
            f"Call [{i}]: params mismatch\ngot  {act['params']!r}\nexp  {exp['params']!r}"
        )

    # Final row state
    for i, row in enumerate(session._current_rows()):
        exp = expected_rows[i]
        assert row["city"] == exp["city"], f"Row {i} city: {row['city']!r} != {exp['city']!r}"
        assert row["state"] == exp["state"], f"Row {i} state: {row['state']!r} != {exp['state']!r}"
        assert row["country"] == exp["country"], f"Row {i} country: {row['country']!r} != {exp['country']!r}"


def _build_normalizer_expected_calls(
    countries_as_states,
    cities_as_states,
    invalid_states,
    state_mappings,
    countries_as_cities,
    states_as_cities,
    invalid_city_patterns,
):
    # Expected SQL is the SQLAlchemy Core rendering of the statements built
    # in pipeline.stages.cleanup.normalizer._statements (str(update(...))).
    calls = []

    _STATE_IN_SQL = "UPDATE jobs SET state=:state WHERE jobs.state IN (__[POSTCOMPILE_state_1])"
    _CITY_LOWER_IN_SQL = "UPDATE jobs SET city=:city WHERE lower(jobs.city) IN (__[POSTCOMPILE_lower_1])"

    for col in ("state", "city", "country"):
        calls.append(
            {
                "sql": (
                    f"UPDATE jobs SET {col}=trim(jobs.{col}) "
                    f"WHERE jobs.{col} IS NOT NULL AND jobs.{col} IS DISTINCT FROM trim(jobs.{col})"
                ),
                "params": {},
            }
        )

    for state, country in countries_as_states.items():
        calls.append(
            {
                "sql": "UPDATE jobs SET state=:state, country=:country WHERE jobs.state = :state_1",
                "params": {"country": country, "state": None, "state_1": state},
            }
        )

    calls.append(
        {
            "sql": _STATE_IN_SQL,
            "params": {"state": None, "state_1": list(cities_as_states.keys())},
        }
    )

    calls.append(
        {
            "sql": _STATE_IN_SQL,
            "params": {"state": None, "state_1": list(invalid_states)},
        }
    )

    for old_state, new_state in state_mappings.items():
        # Identity mappings emit no statement: rewriting a row to the value it
        # already holds costs a row version, WAL, an idx_jobs_state update, and
        # -- because `state` feeds search_vector -- a tsvector recompute plus GIN
        # maintenance, all for no semantic change.
        if new_state is None or new_state == old_state:
            continue
        calls.append(
            {
                "sql": "UPDATE jobs SET state=:state WHERE jobs.state = :state_1",
                "params": {"state": new_state, "state_1": old_state},
            }
        )

    null_mappings = [k for k, v in state_mappings.items() if v is None]
    calls.append(
        {
            "sql": _STATE_IN_SQL,
            "params": {"state": None, "state_1": null_mappings},
        }
    )

    calls.append(
        {
            "sql": _CITY_LOWER_IN_SQL,
            "params": {"city": None, "lower_1": [c.lower() for c in countries_as_cities]},
        }
    )

    calls.append(
        {
            "sql": _CITY_LOWER_IN_SQL,
            "params": {"city": None, "lower_1": [s.lower() for s in states_as_cities]},
        }
    )

    combined = "|".join(invalid_city_patterns)
    calls.append(
        {
            "sql": "UPDATE jobs SET city=:city WHERE jobs.city ~* :city_1",
            "params": {"city": None, "city_1": combined},
        }
    )

    return calls
