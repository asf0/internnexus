"""Pipeline step ordering shared by CLI and runtime state."""

from __future__ import annotations

PIPELINE_STEPS = ("discover", "sync_inactive", "ingest", "delete_inactive", "cleanup", "classify", "embed")

PIPELINE_STEP_SET = set(PIPELINE_STEPS)
