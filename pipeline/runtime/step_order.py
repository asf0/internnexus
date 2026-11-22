"""Pipeline step ordering shared by CLI and runtime state."""

from __future__ import annotations

PIPELINE_STEPS = ("ingest", "delete_inactive", "cleanup", "classify", "embed")

#: Steps that used to exist and may still appear in persisted PipelineRun rows.
#: Each maps to the step a resumed run should continue from.
_RETIRED_STEPS = {
    "sync_inactive": "ingest",
    "discover": "ingest",
}


def get_resume_step(step_completed: str | None) -> str | None:
    """Return the next step for persisted run state, including legacy rows."""
    if not step_completed:
        return PIPELINE_STEPS[0]
    if step_completed in _RETIRED_STEPS:
        return _RETIRED_STEPS[step_completed]
    try:
        index = PIPELINE_STEPS.index(step_completed)
    except ValueError:
        return None
    return PIPELINE_STEPS[index + 1] if index < len(PIPELINE_STEPS) - 1 else None
