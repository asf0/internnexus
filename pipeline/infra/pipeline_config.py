from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

from pipeline.infra.paths import CONFIG_PATH, WORKSPACE_ROOT


class PipelineConfig(BaseModel):
    continuous_interval: int = 3600
    backoff_on_error: int = 300
    max_backoff_multiplier: int = 5
    command_lease_seconds: int = Field(default=86_400, ge=300)


class CleanupConfig(BaseModel):
    parse_concurrency: int = 12
    chunk_size: int = 5000
    location_cache_max_size: int = 10_000
    warm_batch: int = Field(default=500, ge=1)


class IngestConfig(BaseModel):
    slug_chunk_size: int = Field(default=50, ge=1)
    upsert_batch_size: int = Field(default=1000, ge=1)
    # A board fetch that returns far fewer jobs than its last known snapshot
    # (rate limit, pagination bug, JS timeout) looks like a mass closure to a
    # one-shot diff. Preserve the snapshot instead of reconciling when the
    # drop exceeds this ratio, but only above suspicious_drop_min_count -
    # below that, normal single-job turnover would trip the ratio constantly.
    suspicious_drop_ratio: float = Field(default=0.5, gt=0, le=1)
    suspicious_drop_min_count: int = Field(default=20, ge=1)


class SyncConfig(BaseModel):
    min_total_sighting_ratio: float = Field(default=0.5, gt=0, le=1)
    min_source_sighting_ratio: float = Field(default=0.5, gt=0, le=1)
    min_stale_guard_count: int = Field(default=1000, ge=1)
    min_fetched_to_stale_ratio: float = Field(default=0.5, gt=0)
    sightings_retention_days: int = Field(default=7, ge=1)
    sightings_cleanup_batch_size: int = Field(default=50_000, ge=1)
    # Retention for completed/failed pipeline_runs rows. Kept well above
    # sightings_retention_days so a run's sightings are already pruned before the
    # run itself is removed. Running runs are never deleted.
    runs_retention_days: int = Field(default=30, ge=1)
    runs_cleanup_batch_size: int = Field(default=10_000, ge=1)
    sync_batch_size: int = Field(default=5000, ge=1)


class EmbeddingsConfig(BaseModel):
    batch_size: int = 50
    parallel_batches: int = 2
    api_batch_size: int = 32  # texts per embed_many() call; raise to reduce API round-trips
    # The matching query filters candidates to this recency window (jobs with
    # no posted_at are retained). Embedding older jobs is wasted work: the
    # backend drops them after vector retrieval, so they never rank.
    matchable_within_days: int = Field(default=120, ge=1)


class ApiConfig(BaseModel):
    fetch_concurrency: int = 10
    slug_404_cooldown_hours: int = 24


class ClassifyConfig(BaseModel):
    commit_batch_size: int = Field(default=200, ge=1)


class RetryConfig(BaseModel):
    db_max_attempts: int = Field(default=3, ge=1)
    db_base_delay_seconds: float = Field(default=0.5, gt=0)
    db_max_delay_seconds: float = Field(default=4.0, gt=0)


class HealthCheckConfig(BaseModel):
    enabled: bool = True
    timeout: int = 10


class LoggingConfig(BaseModel):
    """Filesystem logging paths, resolved relative to the Ensign directory."""

    logs_dir: Path = WORKSPACE_ROOT / "logs"

    @field_validator("logs_dir", mode="before")
    @classmethod
    def resolve_logs_dir(cls, value: str | Path) -> Path:
        path = Path(value).expanduser()
        if path.is_absolute():
            return path.resolve()
        return (WORKSPACE_ROOT / path).resolve()


class Config(BaseModel):
    pipeline: PipelineConfig = PipelineConfig()
    api: ApiConfig = ApiConfig()
    ingest: IngestConfig = IngestConfig()
    sync: SyncConfig = SyncConfig()
    cleanup: CleanupConfig = CleanupConfig()
    embeddings: EmbeddingsConfig = EmbeddingsConfig()
    classify: ClassifyConfig = ClassifyConfig()
    retry: RetryConfig = RetryConfig()
    health_check: HealthCheckConfig = HealthCheckConfig()
    logging: LoggingConfig = LoggingConfig()


__all__ = ["CONFIG_PATH", "Config", "get_config"]


@lru_cache
def get_config() -> Config:
    if not CONFIG_PATH.exists():
        return Config()

    with open(CONFIG_PATH, "r") as f:
        data = yaml.safe_load(f) or {}

    return Config(**data)
