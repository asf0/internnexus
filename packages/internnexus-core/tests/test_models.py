"""Tests for shared ORM model ownership."""

from internnexus_core.models import Base, Job, PipelineCommand, PipelineJobSighting, PipelineRun


def test_shared_model_tables_are_registered_once() -> None:
    assert {"jobs", "pipeline_job_sightings", "pipeline_runs", "pipeline_commands"}.issubset(Base.metadata.tables)
    assert Job.__table__ is Base.metadata.tables["jobs"]
    assert PipelineJobSighting.__table__ is Base.metadata.tables["pipeline_job_sightings"]
    assert PipelineRun.__table__ is Base.metadata.tables["pipeline_runs"]
    assert PipelineCommand.__table__ is Base.metadata.tables["pipeline_commands"]
