from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
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
    ollama_base_url: str

    # Classification configuration
    classification_model: str | None = None
    classification_timeout_seconds: float = 90.0
    classification_max_concurrent: int = 2
    classification_keep_alive: str = "30m"
    classification_num_predict: int = 64

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
    def resolved_classification_model(self) -> str:
        """Return configured classification model."""
        model = self.classification_model
        if not model:
            raise ValueError("classification model not configured (set CLASSIFICATION_MODEL)")
        return model


@lru_cache
def get_settings() -> Settings:
    # BaseSettings resolves required fields from environment at runtime.
    # Keep this focused suppression until Pyright can model settings injection.
    return Settings()  # pyright: ignore[reportCallIssue]
