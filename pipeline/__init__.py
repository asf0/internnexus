"""Job ingestion pipeline modules."""

import sys
from pathlib import Path

# Add project root and backend to path for clean imports
_project_root = Path(__file__).parent.parent
_backend_dir = _project_root / "backend"
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_backend_dir))

from pipeline.fetch import fetch_and_ingest
from pipeline.cleanup import cleanup_locations
from pipeline.embeddings import generate_embeddings
from pipeline.pipeline import fetch_api_jobs, upsert_jobs

__all__ = [
    "fetch_and_ingest",
    "cleanup_locations",
    "generate_embeddings",
    "fetch_api_jobs",
    "upsert_jobs",
]
