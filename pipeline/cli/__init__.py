"""Pipeline command-line entry points."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import (
        args,
        consolidate_categories,
        run_pipeline,
    )

__all__ = ["args", "consolidate_categories", "run_pipeline"]
