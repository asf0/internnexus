from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class PipelineConfig(BaseModel):
    continuous_interval: int = 3600
    backoff_on_error: int = 300
    max_backoff_multiplier: int = 5


class CleanupConfig(BaseModel):
    process_all: bool = False
    parse_concurrency: int = 12
    chunk_size: int = 5000
    location_cache_max_size: int = 10_000


class IngestConfig(BaseModel):
    slug_chunk_size: int = Field(default=50, ge=1)
    upsert_batch_size: int = Field(default=1000, ge=1)


class SyncConfig(BaseModel):
    min_total_sighting_ratio: float = Field(default=0.5, gt=0, le=1)
    min_source_sighting_ratio: float = Field(default=0.5, gt=0, le=1)
    min_stale_guard_count: int = Field(default=1000, ge=1)
    min_fetched_to_stale_ratio: float = Field(default=0.5, gt=0)
    sightings_retention_days: int = Field(default=7, ge=1)
    sightings_cleanup_batch_size: int = Field(default=50_000, ge=1)
    sync_batch_size: int = Field(default=5000, ge=1)


class EmbeddingsConfig(BaseModel):
    batch_size: int = 50
    parallel_batches: int = 2
    api_batch_size: int = 16  # texts per embed_many() call; raise to reduce API round-trips


class ApiConfig(BaseModel):
    fetch_concurrency: int = 10
    slug_404_cooldown_hours: int = 24


class ClassifyConfig(BaseModel):
    commit_batch_size: int = Field(default=200, ge=1)


class RetryConfig(BaseModel):
    db_max_attempts: int = Field(default=3, ge=1)
    db_base_delay_seconds: float = Field(default=0.5, gt=0)
    db_max_delay_seconds: float = Field(default=4.0, gt=0)


class DiscoveryConfig(BaseModel):
    enabled: bool = True
    timeout: int = 15
    searxng_url: str = ""
    query_delay_seconds: float = 0.25
    max_pages: int | None = None
    countries: list[str] = [
        "United States",
        "Brazil",
        "Korea",
        "Ireland",
        "Canada",
        "United Kingdom",
        "Germany",
    ]


class HealthCheckConfig(BaseModel):
    enabled: bool = True
    timeout: int = 10


class Config(BaseModel):
    pipeline: PipelineConfig = PipelineConfig()
    api: ApiConfig = ApiConfig()
    ingest: IngestConfig = IngestConfig()
    sync: SyncConfig = SyncConfig()
    cleanup: CleanupConfig = CleanupConfig()
    embeddings: EmbeddingsConfig = EmbeddingsConfig()
    classify: ClassifyConfig = ClassifyConfig()
    retry: RetryConfig = RetryConfig()
    discovery: DiscoveryConfig = DiscoveryConfig()
    health_check: HealthCheckConfig = HealthCheckConfig()


CONFIG_PATH = Path(__file__).resolve().parents[1] / "pipeline.yaml"


@lru_cache
def get_config() -> Config:
    if not CONFIG_PATH.exists():
        return Config()

    with open(CONFIG_PATH, "r") as f:
        data = yaml.safe_load(f) or {}

    return Config(**data)
