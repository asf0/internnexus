"""Detect schema drift between backend and pipeline shared models.

This test intentionally imports both service model modules so CI can fail if
shared tables (jobs, pipeline_runs, pipeline_commands) diverge.  It does not
move any model code; it is pure drift detection.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Provide fallback env values so pipeline.config can load even if some vars are
# missing from the backend test environment.
_ENV_DEFAULTS = {
    "POSTGRES_DB": "test",
    "POSTGRES_USER": "test",
    "POSTGRES_PASSWORD": "test",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "EMBEDDING_PROVIDER": "ollama",
    "EMBEDDING_MODEL": "test-model",
    "EMBEDDING_DIMENSIONS": "2560",
    "OLLAMA_BASE_URL": "http://localhost:11434",
    "GREENHOUSE_API_URL": "https://example.com",
    "LEVER_API_URL": "https://example.com",
    "SIMPLIFY_JOBS_INTERN_URL": "https://example.com/intern",
    "SIMPLIFY_JOBS_NEW_GRAD_URL": "https://example.com/newgrad",
}
for key, value in _ENV_DEFAULTS.items():
    os.environ.setdefault(key, value)

from app.models import Job as BackendJob  # noqa: E402
from app.models import PipelineCommand as BackendPipelineCommand  # noqa: E402
from app.models import PipelineRun as BackendPipelineRun  # noqa: E402
from pipeline.models import Job as PipelineJob  # noqa: E402
from pipeline.models import PipelineCommand as PipelinePipelineCommand  # noqa: E402
from pipeline.models import PipelineRun as PipelinePipelineRun  # noqa: E402


def _column_spec(model: Any) -> dict[str, str]:
    """Return {column_name: type_repr} for a declarative model."""
    return {column.name: str(column.type) for column in model.__table__.columns}


def test_job_columns_match_pipeline():
    """Backend and pipeline Job models must define the same columns."""
    backend_columns = _column_spec(BackendJob)
    pipeline_columns = _column_spec(PipelineJob)
    assert backend_columns == pipeline_columns, (
        f"Job column drift detected:\nbackend={backend_columns}\n"
        f"pipeline={pipeline_columns}"
    )


def test_pipeline_run_columns_match():
    """Backend and pipeline PipelineRun models must define the same columns."""
    assert _column_spec(BackendPipelineRun) == _column_spec(PipelinePipelineRun)


def test_pipeline_command_columns_match():
    """Backend and pipeline PipelineCommand models must define the same columns."""
    assert _column_spec(BackendPipelineCommand) == _column_spec(PipelinePipelineCommand)
