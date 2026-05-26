from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.domain import JobSchema


def test_job_schema_accepts_scraper_sources() -> None:
    linkedin_job = JobSchema(
        source="linkedin_scrape",
        title="Software Engineer",
        company="Acme",
        location="Remote",
        apply_url="https://example.com/linkedin",
        description_text="desc",
    )
    indeed_job = JobSchema(
        source="indeed_scrape",
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        apply_url="https://example.com/indeed",
        description_text="desc",
    )

    assert linkedin_job.source == "linkedin_scrape"
    assert indeed_job.source == "indeed_scrape"
