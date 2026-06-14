from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Protocol, cast

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int

    # Embedding configuration
    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int = 2560
    ollama_base_url: str

    # Auth/JWT configuration
    auth_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    app_name: str = "InternNexus API"

    # OAuth token encryption (RSA keys in PEM format)
    # Public key is required for encryption, private key for decryption
    oauth_encryption_public_key_b64: str = ""
    oauth_encryption_private_key_b64: str = ""

    # OAuth provider settings are consumed by the frontend, but declaring them
    # here lets the backend fail fast if OAuth is enabled without token keys.
    gh_client_id: str = ""
    gh_client_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""

    # Redis configuration (optional; in-memory TTL cache is used when empty)
    redis_url: str = ""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("embedding_dimensions")
    @classmethod
    def validate_embedding_dimensions(cls, value: int) -> int:
        if not 32 <= value <= 2560:
            raise ValueError("embedding_dimensions must be between 32 and 2560")
        return value

    @field_validator("auth_secret")
    @classmethod
    def validate_auth_secret_strength(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("auth_secret must be at least 32 characters for security")
        return v

    @model_validator(mode="after")
    def validate_oauth_encryption_keys(self) -> "Settings":
        oauth_configured = any(
            value.strip()
            for value in (
                self.gh_client_id,
                self.gh_client_secret,
                self.google_client_id,
                self.google_client_secret,
            )
        )
        if not oauth_configured:
            return self

        missing = []
        if not self.oauth_encryption_public_key_b64.strip():
            missing.append("OAUTH_ENCRYPTION_PUBLIC_KEY_B64")
        if not self.oauth_encryption_private_key_b64.strip():
            missing.append("OAUTH_ENCRYPTION_PRIVATE_KEY_B64")
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"OAuth encryption keys are required when OAuth providers are configured: {joined}")
        return self

    @property
    def resolved_database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    class _SettingsFactory(Protocol):
        def __call__(self) -> Settings: ...

    # BaseSettings resolves required fields from environment at runtime.
    # Cast the class constructor to a zero-arg factory for static checking.
    settings_factory = cast(_SettingsFactory, Settings)
    return settings_factory()
