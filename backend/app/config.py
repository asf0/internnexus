from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from typing import Any
from pydantic_settings import BaseSettings, SettingsConfigDict

VisaResult = dict[str, Any]


class Settings(BaseSettings):
    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int
    # database_url: str

    # Embedding configuration
    embedding_provider: str
    embedding_model: str
    ollama_base_url: str
    # Auth/JWT configuration
    auth_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    app_name: str = "InternNexus API"

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

    @property
    def resolved_database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
