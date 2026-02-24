from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

VisaResult = dict[str, Any]


class Settings(BaseSettings):
    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int

    # Embedding configuration
    embedding_provider: str
    embedding_model: str
    ollama_base_url: str

    # Classification configuration
    classification_model: str
    ollama_classification_url: str | None = None  # Defaults to ollama_base_url if not set

    # Auth/JWT configuration
    auth_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    app_name: str = "InternNexus API"

    # OAuth token encryption (RSA keys in PEM format)
    # Public key is required for encryption, private key for decryption
    oauth_encryption_public_key_b64: str = ""
    oauth_encryption_private_key_b64: str = ""

    # Redis configuration
    redis_url: str

    # External API URLs (public endpoints)
    greenhouse_api_url: str
    lever_api_url: str
    simplify_jobs_intern_url: str
    simplify_jobs_new_grad_url: str

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    visa_classifier_model: str | None = None

    @field_validator("auth_secret")
    @classmethod
    def validate_auth_secret_strength(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("auth_secret must be at least 32 characters for security")
        return v

    @property
    def resolved_database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def resolved_classification_url(self) -> str:
        """Return classification URL, defaulting to ollama_base_url if not set."""
        return self.ollama_classification_url or self.ollama_base_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
