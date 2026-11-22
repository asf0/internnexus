"""Pipeline-compatible re-exports of shared ORM mappings and job enums."""

from internnexus_core.jobs import JobSource, JobType, WorkMode
from internnexus_core.models import (
    Base,
    Job,
    JobBoardSnapshot,
    PipelineCommand,
    PipelineCommandStatus,
    PipelineJobSighting,
    PipelineRun,
    PipelineRunStatus,
    PipelineSyncState,
)

__all__ = [
    "Base",
    "Job",
    "JobBoardSnapshot",
    "JobSource",
    "JobType",
    "PipelineCommand",
    "PipelineCommandStatus",
    "PipelineJobSighting",
    "PipelineRun",
    "PipelineRunStatus",
    "PipelineSyncState",
    "WorkMode",
]
