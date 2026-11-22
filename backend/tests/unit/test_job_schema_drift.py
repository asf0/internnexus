"""Verify backend and pipeline consume the same shared ORM mappings."""

from __future__ import annotations

import os
import sys

from tests.paths import REPO_ROOT

PROJECT_ROOT = REPO_ROOT
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Provide fallback env values so pipeline.infra.settings can load even if some vars are
# missing from the backend test environment.
_ENV_DEFAULTS = {
    "POSTGRES_DB": "test",
    "POSTGRES_USER": "test",
    "POSTGRES_PASSWORD": "test",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "EMBEDDING_MODEL": "test-model",
    "EMBEDDING_DIMENSIONS": "1024",
    "OPENAI_BASE_URL": "http://192.168.0.4:8080/v1",
    "GREENHOUSE_API_URL": "https://example.com",
    "LEVER_API_URL": "https://example.com",
    "SIMPLIFY_JOBS_INTERN_URL": "https://example.com/intern",
    "SIMPLIFY_JOBS_NEW_GRAD_URL": "https://example.com/newgrad",
}
for key, value in _ENV_DEFAULTS.items():
    os.environ.setdefault(key, value)

from internnexus_core.models import (  # noqa: E402
    Job as CoreJob,
    PipelineCommand as CorePipelineCommand,
    PipelineJobSighting as CorePipelineJobSighting,
    PipelineRun as CorePipelineRun,
)

from app.models import Job as BackendJob  # noqa: E402
from app.models import PipelineCommand as BackendPipelineCommand  # noqa: E402
from app.models import PipelineJobSighting as BackendPipelineJobSighting  # noqa: E402
from app.models import PipelineRun as BackendPipelineRun  # noqa: E402
from pipeline.infra.models import Job as PipelineJob  # noqa: E402
from pipeline.infra.models import PipelineCommand as PipelinePipelineCommand  # noqa: E402
from pipeline.infra.models import PipelineJobSighting as PipelinePipelineJobSighting  # noqa: E402
from pipeline.infra.models import PipelineRun as PipelinePipelineRun  # noqa: E402


def test_shared_model_identity():
    """Both service namespaces must re-export each core table class exactly."""
    assert BackendJob is PipelineJob is CoreJob
    assert BackendPipelineJobSighting is PipelinePipelineJobSighting is CorePipelineJobSighting
    assert BackendPipelineRun is PipelinePipelineRun is CorePipelineRun
    assert BackendPipelineCommand is PipelinePipelineCommand is CorePipelineCommand


def test_shared_model_table_names_are_stable():
    assert CoreJob.__tablename__ == "jobs"
    assert CorePipelineJobSighting.__tablename__ == "pipeline_job_sightings"
    assert CorePipelineRun.__tablename__ == "pipeline_runs"
    assert CorePipelineCommand.__tablename__ == "pipeline_commands"
