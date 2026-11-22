"""Regression test locking in the pgbouncer routing invariant.

`backend` and `mcp` are long-lived services that may safely route through the
transaction-mode `pgbouncer` service. `migrate` (runs DDL) and `pipeline`
(holds a session-level Postgres advisory lock for the whole run; see
pipeline/runtime/sync_lock.py) are INCOMPATIBLE with transaction pooling and
MUST keep connecting directly to `db`. This test parses docker-compose.yml
and asserts the effective POSTGRES_HOST resolved for each service, so a
future compose edit that reroutes pipeline/migrate through pgbouncer (or
stops routing backend/mcp through it) fails loudly.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_PATH = REPOSITORY_ROOT / "docker-compose.yml"


def _load_compose() -> dict[str, Any]:
    """Load docker-compose.yml, relying on PyYAML's native `<<` merge-key
    support to resolve the `x-db-env` anchor merge (later same-key entries
    in a service's own `environment` block override the merged-in anchor
    value, per YAML merge-key semantics)."""
    with COMPOSE_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _effective_postgres_host(services: dict[str, Any], service_name: str) -> str:
    environment = services[service_name]["environment"]
    assert isinstance(environment, dict), (
        f"expected '{service_name}.environment' to resolve to a mapping "
        f"(merge keys expanded), got {type(environment)!r}"
    )
    assert "POSTGRES_HOST" in environment, f"'{service_name}' has no POSTGRES_HOST set"
    return environment["POSTGRES_HOST"]


@pytest.fixture(scope="module")
def compose() -> dict[str, Any]:
    return _load_compose()


@pytest.fixture(scope="module")
def services(compose: dict[str, Any]) -> dict[str, Any]:
    return compose["services"]


def test_merge_key_anchor_actually_expands_to_a_mapping(services: dict[str, Any]) -> None:
    """Sanity-check the YAML anchor/merge assumption the other assertions rely on."""
    for name in ("pipeline", "migrate", "backend", "mcp"):
        assert isinstance(services[name]["environment"], dict)
    # The shared anchor sets these on every merging service.
    for name in ("pipeline", "migrate", "backend", "mcp"):
        env = services[name]["environment"]
        assert env.get("POSTGRES_PORT") in ("5432", "6432")


def test_pipeline_connects_directly_to_db(services: dict[str, Any]) -> None:
    assert _effective_postgres_host(services, "pipeline") == "db"


def test_migrate_connects_directly_to_db(services: dict[str, Any]) -> None:
    assert _effective_postgres_host(services, "migrate") == "db"


def test_backend_routes_through_pgbouncer(services: dict[str, Any]) -> None:
    assert _effective_postgres_host(services, "backend") == "pgbouncer"


def test_mcp_routes_through_pgbouncer(services: dict[str, Any]) -> None:
    assert _effective_postgres_host(services, "mcp") == "pgbouncer"


def test_pgbouncer_service_runs_in_transaction_pool_mode(services: dict[str, Any]) -> None:
    assert "pgbouncer" in services
    pgbouncer_env = services["pgbouncer"]["environment"]
    assert pgbouncer_env.get("POOL_MODE") == "transaction"


def test_regression_detector_actually_catches_a_pipeline_reroute(services: dict[str, Any]) -> None:
    """Meta-test: prove the assertion above is not vacuous by flipping
    pipeline's resolved host to pgbouncer on an in-memory copy only (the
    on-disk compose file is never touched) and confirming detection fails."""
    tampered = copy.deepcopy(services)
    tampered["pipeline"]["environment"]["POSTGRES_HOST"] = "pgbouncer"

    with pytest.raises(AssertionError):
        assert _effective_postgres_host(tampered, "pipeline") == "db"

    # The real, on-disk services are untouched by the tamper above.
    assert _effective_postgres_host(services, "pipeline") == "db"
