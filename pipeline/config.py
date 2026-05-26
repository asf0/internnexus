from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Protocol, cast

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int

    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int = 2560
    ollama_base_url: str
    ollama_classification_url: str | None = None

    classification_model: str | None = None
    classification_timeout_seconds: float = 90.0
    classification_max_concurrent: int = 2
    classification_batch_size: int = 10
    classification_keep_alive: str = "30m"
    classification_num_predict: int = 64

    greenhouse_api_url: str
    lever_api_url: str
    simplify_jobs_intern_url: str
    simplify_jobs_new_grad_url: str

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[1] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("classification_batch_size")
    @classmethod
    def validate_classification_batch_size(cls, value: int) -> int:
        if not 1 <= value <= 50:
            raise ValueError("classification_batch_size must be between 1 and 50")
        return value

    @field_validator("embedding_dimensions")
    @classmethod
    def validate_embedding_dimensions(cls, value: int) -> int:
        if not 32 <= value <= 2560:
            raise ValueError("embedding_dimensions must be between 32 and 2560")
        return value

    @property
    def resolved_database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def resolved_classification_model(self) -> str:
        model = self.classification_model
        if not model:
            raise ValueError("classification model not configured (set CLASSIFICATION_MODEL)")
        return model


@lru_cache
def get_settings() -> Settings:
    class _SettingsFactory(Protocol):
        def __call__(self) -> Settings: ...

    settings_factory = cast(_SettingsFactory, Settings)
    return settings_factory()
