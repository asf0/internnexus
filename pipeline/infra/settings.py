from __future__ import annotations


from pydantic import field_validator
from pydantic_settings import SettingsConfigDict

from internnexus_core.config import PostgresSettingsMixin, make_settings_loader
from pipeline.infra.paths import ENV_FILE


class Settings(PostgresSettingsMixin):
    db_pool_size: int = 2
    db_max_overflow: int = 2

    embedding_model: str
    embedding_dimensions: int = 1024
    openai_base_url: str
    embedding_timeout_seconds: float = 180.0
    openai_classification_url: str | None = None

    classification_model: str | None = None
    classification_timeout_seconds: float = 90.0
    classification_max_concurrent: int = 4
    classification_batch_size: int = 20
    classification_temperature: float = 0.0
    classification_openai_max_tokens: int = 64
    classification_openai_batch_min_tokens: int = 256
    classification_openai_batch_tokens_per_job: int = 48
    classification_parse_retry_attempts: int = 2

    greenhouse_api_url: str
    lever_api_url: str
    ashby_api_url: str
    simplify_jobs_intern_url: str
    simplify_jobs_new_grad_url: str

    # Private frontend endpoint used after public job-detail writes commit.
    frontend_internal_url: str = ""
    job_cache_revalidation_secret: str = ""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("db_pool_size")
    @classmethod
    def validate_pool_size(cls, value: int) -> int:
        if not 1 <= value <= 50:
            raise ValueError("db_pool_size must be between 1 and 50")
        return value

    @field_validator("db_max_overflow")
    @classmethod
    def validate_pool_overflow(cls, value: int) -> int:
        if not 0 <= value <= 50:
            raise ValueError("db_max_overflow must be between 0 and 50")
        return value

    @field_validator("classification_batch_size")
    @classmethod
    def validate_classification_batch_size(cls, value: int) -> int:
        if not 1 <= value <= 50:
            raise ValueError("classification_batch_size must be between 1 and 50")
        return value

    @field_validator("embedding_dimensions")
    @classmethod
    def validate_embedding_dimensions(cls, value: int) -> int:
        if value != 1024:
            raise ValueError(
                "embedding_dimensions must equal 1024 (the column dimension); "
                "create a migration before changing it"
            )
        return value

    @property
    def resolved_classification_model(self) -> str:
        model = self.classification_model
        if not model:
            raise ValueError("classification model not configured (set CLASSIFICATION_MODEL)")
        return model


get_settings = make_settings_loader(Settings)
