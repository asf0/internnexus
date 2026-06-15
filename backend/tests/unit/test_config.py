from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


def _settings_kwargs(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "postgres_db": "test_db",
        "postgres_user": "test",
        "postgres_password": "test",
        "postgres_host": "localhost",
        "postgres_port": 5432,
        "embedding_provider": "openai",
        "embedding_model": "qwen3-embedding-4b",
        "openai_base_url": "http://localhost:8080/v1",
        "auth_secret": "x" * 32,
        "oauth_encryption_public_key_b64": "",
        "oauth_encryption_private_key_b64": "",
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


def test_oauth_keys_not_required_when_oauth_is_not_configured() -> None:
    settings = Settings(**_settings_kwargs())

    assert settings.oauth_encryption_public_key_b64 == ""
    assert settings.oauth_encryption_private_key_b64 == ""


def test_oauth_keys_required_when_provider_is_configured() -> None:
    with pytest.raises(ValidationError, match="OAUTH_ENCRYPTION_PUBLIC_KEY_B64"):
        Settings(**_settings_kwargs(gh_client_id="github-client-id"))


def test_oauth_provider_configuration_accepts_encryption_keys() -> None:
    settings = Settings(
        **_settings_kwargs(
            gh_client_id="github-client-id",
            oauth_encryption_public_key_b64="public-key",
            oauth_encryption_private_key_b64="private-key",
        )
    )

    assert settings.gh_client_id == "github-client-id"
