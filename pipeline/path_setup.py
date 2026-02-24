"""Shared path setup for pipeline entrypoint scripts."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_project_paths() -> None:
    """Ensure project root and backend package paths are importable."""
    project_root = Path(__file__).parent.parent
    backend_dir = project_root / "backend"

    project_root_str = str(project_root)
    backend_dir_str = str(backend_dir)

    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    if backend_dir_str not in sys.path:
        sys.path.insert(0, backend_dir_str)
