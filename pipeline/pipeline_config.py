from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel


class PipelineConfig(BaseModel):
    continuous_interval: int = 3600
    backoff_on_error: int = 300
    max_backoff_multiplier: int = 5


class CleanupConfig(BaseModel):
    process_all: bool = False
    parse_concurrency: int = 12
    chunk_size: int = 5000


class EmbeddingsConfig(BaseModel):
    batch_size: int = 50
    parallel_batches: int = 2
    api_batch_size: int = 16  # texts per embed_many() call; raise to reduce API round-trips


class ApiConfig(BaseModel):
    fetch_concurrency: int = 10
    slug_404_cooldown_hours: int = 24


class DiscoveryConfig(BaseModel):
    enabled: bool = True
    timeout: int = 300


class HealthCheckConfig(BaseModel):
    enabled: bool = True
    timeout: int = 10


class Config(BaseModel):
    pipeline: PipelineConfig = PipelineConfig()
    api: ApiConfig = ApiConfig()
    cleanup: CleanupConfig = CleanupConfig()
    embeddings: EmbeddingsConfig = EmbeddingsConfig()
    discovery: DiscoveryConfig = DiscoveryConfig()
    health_check: HealthCheckConfig = HealthCheckConfig()


CONFIG_PATH = Path(__file__).parent / "pipeline.yaml"


@lru_cache
def get_config() -> Config:
    if not CONFIG_PATH.exists():
        return Config()

    with open(CONFIG_PATH, "r") as f:
        data = yaml.safe_load(f) or {}

    return Config(**data)
