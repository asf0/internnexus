"""Focused regression tests for the database I/O remediation."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from pipeline.stages.cleanup.normalizer import _normalize_existing_states
from pipeline.domain import JobSchema
from pipeline.domain.sync_result import IngestResult, SourceFetchStats
from pipeline.repositories.job_upsert import build_job_rows, changed_only_job_upsert
from pipeline.stages.ingest.upsert import upsert_jobs
from internnexus_core.text import embedding_input_hash
from pipeline.runtime.orchestrator import PipelineRunner, SyncSafetyAssessment, _assess_sync_safety
from pipeline.runtime import services as runtime_services
from pipeline.stages.ingest.sources.greenhouse import GreenhouseClient


class _RowCountResult:
    rowcount = 0


class _StatementCaptureSession:
    def __init__(self):
        self.statements = []

    async def execute(self, statement, _parameters=None):
        self.statements.append(statement)
        return _RowCountResult()

    async def commit(self):
        return None


@pytest.mark.asyncio
async def test_location_trimming_skips_already_normalized_rows() -> None:
    session = _StatementCaptureSession()

    await _normalize_existing_states(session)

    trim_statements = [str(statement).upper() for statement in session.statements[:3]]
    assert all("IS DISTINCT FROM TRIM" in statement for statement in trim_statements)
