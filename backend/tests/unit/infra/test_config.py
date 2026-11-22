from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.infra.config import Settings


def _settings_kwargs(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "postgres_db": "test_db",
        "postgres_user": "test",
        "postgres_password": "test",
        "postgres_host": "localhost",
        "postgres_port": 5432,
        "embedding_model": "qwen3-embedding-4b",
        "openai_base_url": "http://localhost:8080/v1",
        "auth_secret": "x" * 32,
        "gh_client_id": "",
        "gh_client_secret": "",
        "google_client_id": "",
        "google_client_secret": "",
    }
    values.update(overrides)
    return values


def test_redis_url_defaults_to_empty() -> None:
    settings = Settings(**_settings_kwargs(redis_url=""))
    assert settings.redis_url == ""


def test_database_pool_defaults_are_conservative() -> None:
    settings = Settings(**_settings_kwargs())

    assert settings.db_pool_size == 5
    assert settings.db_max_overflow == 5


def test_db_statement_cache_size_defaults_to_none() -> None:
    settings = Settings(**_settings_kwargs())

    assert settings.db_statement_cache_size is None


def test_db_statement_cache_size_can_be_overridden() -> None:
    settings = Settings(**_settings_kwargs(db_statement_cache_size=0))

    assert settings.db_statement_cache_size == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [("db_pool_size", 0), ("db_pool_size", 51), ("db_max_overflow", -1), ("db_max_overflow", 51)],
)
def test_database_pool_limits_reject_unsafe_values(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        Settings(**_settings_kwargs(**{field: value}))


def test_jwt_expiration_must_be_positive() -> None:
    with pytest.raises(ValidationError, match="at least 1"):
        Settings(**_settings_kwargs(jwt_expiration_hours=0))


def test_oauth_providers_are_disabled_when_not_configured() -> None:
    settings = Settings(**_settings_kwargs())

    assert settings.gh_client_id == ""
    assert settings.google_client_id == ""


@pytest.mark.parametrize(
    "overrides",
    [
        {"gh_client_id": "github-client-id"},
        {"google_client_secret": "google-secret"},
    ],
)
def test_oauth_provider_configuration_requires_complete_pairs(overrides: dict[str, str]) -> None:
    with pytest.raises(ValidationError, match="complete client ID/secret pairs"):
        Settings(**_settings_kwargs(**overrides))


def test_oauth_provider_configuration_accepts_complete_pair() -> None:
    settings = Settings(
        **_settings_kwargs(gh_client_id="github-client-id", gh_client_secret="github-secret")
    )
    assert settings.gh_client_id == "github-client-id"


def test_match_weights_must_sum_to_one() -> None:
    with pytest.raises(ValidationError, match="must sum to 1.0"):
        Settings(**_settings_kwargs(match_weight_semantic=0.9, match_weight_skill_title=0.9))


@pytest.mark.parametrize("value", [-0.1, 1.1, float("inf"), float("nan")])
def test_match_weights_reject_out_of_range_and_non_finite(value: float) -> None:
    with pytest.raises(ValidationError):
        Settings(**_settings_kwargs(match_weight_semantic=value))


@pytest.mark.parametrize("field", ["match_rerank_pool", "match_fallback_count"])
def test_match_pool_and_fallback_must_be_positive(field: str) -> None:
    with pytest.raises(ValidationError):
        Settings(**_settings_kwargs(**{field: 0}))
