from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.domain import JobSchema
from pipeline.domain.schemas import JobSource as DomainJobSource
from pipeline.models import JobSource as OrmJobSource


def test_job_schema_accepts_only_database_sources() -> None:
    for source in ("greenhouse", "lever", "ashby", "manual"):
        job = JobSchema(
            source=source,
            title="Software Engineer",
            company="Acme",
            location="Remote",
            apply_url=f"https://example.com/{source}",
            description_text="desc",
        )
        assert job.source == source


@pytest.mark.parametrize("source", ["linkedin_scrape", "indeed_scrape"])
def test_job_schema_rejects_scraper_sources(source: str) -> None:
    with pytest.raises(ValidationError):
        JobSchema(
            source=source,
            title="Software Engineer",
            company="Acme",
            location="Remote",
            apply_url="https://example.com/apply",
            description_text="desc",
        )


def test_domain_job_sources_match_orm_enum() -> None:
    domain_sources = set(DomainJobSource.__args__)
    orm_sources = {source.value for source in OrmJobSource}

    assert domain_sources == orm_sources
    for source in domain_sources:
        assert OrmJobSource(source).value == source


def test_job_schema_accepted_sources_convert_to_orm_enum() -> None:
    job = JobSchema(
        source="greenhouse",
        title="Software Engineer",
        company="Acme",
        location="Remote",
        apply_url="https://example.com/apply",
        description_text="desc",
    )

    assert OrmJobSource(job.source) is OrmJobSource.greenhouse
