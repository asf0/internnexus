"""Tests for pipeline Settings db_pool_size / db_max_overflow defaults and validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pipeline.infra.settings import Settings

_ENV_VARS = ("DB_POOL_SIZE", "DB_MAX_OVERFLOW")


def _settings_kwargs(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "postgres_db": "test_db",
        "postgres_user": "test",
        "postgres_password": "test",
        "postgres_host": "localhost",
        "postgres_port": 5432,
        "embedding_model": "qwen3-embedding-4b",
        "openai_base_url": "http://localhost:8080/v1",
        "greenhouse_api_url": "http://localhost/greenhouse",
        "lever_api_url": "http://localhost/lever",
        "ashby_api_url": "http://localhost/ashby",
        "simplify_jobs_intern_url": "http://localhost/intern",
        "simplify_jobs_new_grad_url": "http://localhost/new-grad",
    }
    values.update(overrides)
    return values


@pytest.fixture(autouse=True)
def _isolate_pool_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure DB_POOL_SIZE/DB_MAX_OVERFLOW never leak in from the shell or repo .env."""
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_database_pool_defaults_are_conservative() -> None:
    settings = Settings(**_settings_kwargs())

    assert settings.db_pool_size == 2
    assert settings.db_max_overflow == 2


def test_database_pool_size_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_POOL_SIZE", "10")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "7")

    settings = Settings(**_settings_kwargs())

    assert settings.db_pool_size == 10
    assert settings.db_max_overflow == 7


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("db_pool_size", 1),
        ("db_pool_size", 50),
        ("db_max_overflow", 0),
        ("db_max_overflow", 50),
    ],
)
def test_database_pool_limits_accept_boundary_values(field: str, value: int) -> None:
    settings = Settings(**_settings_kwargs(**{field: value}))

    assert getattr(settings, field) == value


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("db_pool_size", 0),
        ("db_pool_size", 51),
        ("db_max_overflow", -1),
        ("db_max_overflow", 51),
    ],
)
def test_database_pool_limits_reject_unsafe_values(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        Settings(**_settings_kwargs(**{field: value}))
