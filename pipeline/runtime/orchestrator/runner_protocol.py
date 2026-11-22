"""Structural contract for the assembled :class:`PipelineRunner`.

The runner is assembled from mixins so each concern lives in its own module
while ``PipelineRunner`` stays a single class: callers and tests override
steps by assigning to the instance (``runner.step_ingest = ...``), which only
works while these remain ordinary methods.

Mixins type-check against this protocol, which declares the shared state and
the methods that cross a mixin boundary. It is not instantiated.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

__all__ = ["RunnerProtocol"]


class RunnerProtocol(Protocol):
    """Shared runner state plus the cross-mixin methods each mixin may call."""

    config: Any
    dry_run: bool
    process_all: bool
    resume_run_id: UUID | None
    test_mode: bool
    limit: int | None
    state_manager_class: Any
    get_incomplete_run_func: Any
    get_resumable_run_func: Any
    get_last_completed_run_started_at_func: Any
    sync_lock_factory: Any
    classify_commit_batch_size: int
    results: dict[str, Any]
    step_times: dict[str, float]
    current_step: str | None

    async def step_mark_stale_jobs(self, state: Any, sync_id: UUID) -> int:
        """Defined by :class:`~.steps.StepsMixin`."""
        ...

    async def cleanup_sync_sightings(self, sync_id: UUID, session: Any = None) -> None:
        """Defined by :class:`~.sync_safety.SyncSafetyMixin`."""
        ...
