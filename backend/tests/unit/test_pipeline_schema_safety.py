from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.schemas import (
    AshbyJobMetadataSchema,
    GreenhouseJobMetadataSchema,
    JobSchema,
    LeverJobMetadataSchema,
)


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


def test_metadata_schema_defaults_do_not_share_mutable_state() -> None:
    now = datetime.now(timezone.utc)

    gh_a = GreenhouseJobMetadataSchema(
        external_id="1",
        internal_job_id=123,
        requisition_id="req-1",
        first_published=now,
        updated_at=now,
        hosted_url="https://example.com/gh",
    )
    gh_b = GreenhouseJobMetadataSchema(
        external_id="2",
        internal_job_id=456,
        requisition_id="req-2",
        first_published=now,
        updated_at=now,
        hosted_url="https://example.com/gh2",
    )
    gh_a.departments.append({"name": "Engineering"})
    assert gh_b.departments == []

    lever_a = LeverJobMetadataSchema(
        external_id="3",
        commitment="Full Time",
        department="Engineering",
        team="Platform",
        workplace_type="remote",
        description_html="<p>desc</p>",
        description_plain="desc",
        hosted_url="https://example.com/lever",
        created_at_raw=123,
    )
    lever_b = LeverJobMetadataSchema(
        external_id="4",
        commitment="Full Time",
        department="Engineering",
        team="Platform",
        workplace_type="remote",
        description_html="<p>desc</p>",
        description_plain="desc",
        hosted_url="https://example.com/lever2",
        created_at_raw=456,
    )
    lever_a.requirements.append({"x": 1})
    assert lever_b.requirements == []

    ashby_a = AshbyJobMetadataSchema(
        external_id="5",
        department="Legal",
        team="Legal",
        employment_type="FullTime",
        location_raw="San Francisco",
        address_locality="San Francisco",
        address_region="California",
        address_country="United States",
        description_html="<p>desc</p>",
        description_plain="desc",
        job_url="https://example.com/ashby",
        updated_at=now,
    )
    ashby_b = AshbyJobMetadataSchema(
        external_id="6",
        department="Legal",
        team="Legal",
        employment_type="FullTime",
        location_raw="San Francisco",
        address_locality="San Francisco",
        address_region="California",
        address_country="United States",
        description_html="<p>desc</p>",
        description_plain="desc",
        job_url="https://example.com/ashby2",
        updated_at=now,
    )
    ashby_a.compensation["currency"] = "USD"
    assert ashby_b.compensation == {}
