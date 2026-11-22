"""Pipeline orchestration: the runner, its steps, and its safety guards.

``PipelineRunner`` is assembled from mixins defined in the sibling modules:

- :mod:`.steps` — the individual ``step_*`` methods
- :mod:`.sync_safety` — guards that gate stale-job mutation
- :mod:`.summary` — end-of-run reporting
"""

from pipeline.runtime.orchestrator.runner import (
    PipelineRunner,
    _should_run,
)
from pipeline.runtime.orchestrator.summary import _log_step_rate
from pipeline.runtime.orchestrator.sync_safety import (
    SyncSafetyAssessment,
    _assess_sync_safety,
)

__all__ = [
    "PipelineRunner",
    "SyncSafetyAssessment",
    "_assess_sync_safety",
    "_log_step_rate",
    "_should_run",
]
