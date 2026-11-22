"""Tests for final classification and embedding cleanup contracts."""

from __future__ import annotations

from pipeline.tests.paths import WORKSPACE_ROOT
from pathlib import Path

from pipeline.infra.settings import Settings
from pipeline.infra.pipeline_config import LoggingConfig


def test_logging_config_default_preserves_existing_absolute_location() -> None:
    expected = WORKSPACE_ROOT / "logs"
    assert LoggingConfig().logs_dir == expected


def test_logging_config_relative_override_uses_deterministic_base() -> None:
    base = WORKSPACE_ROOT
    assert LoggingConfig(logs_dir=Path("var/pipeline-logs")).logs_dir == (base / "var" / "pipeline-logs")


def test_logging_config_preserves_absolute_override(tmp_path: Path) -> None:
    assert LoggingConfig(logs_dir=tmp_path).logs_dir == tmp_path.resolve()


def test_classification_request_parameter_defaults_are_preserved() -> None:
    fields = Settings.model_fields
    assert fields["classification_temperature"].default == 0.0
    assert fields["classification_openai_max_tokens"].default == 64
    assert fields["classification_openai_batch_min_tokens"].default == 256
    assert fields["classification_openai_batch_tokens_per_job"].default == 48
    assert fields["classification_parse_retry_attempts"].default == 2
