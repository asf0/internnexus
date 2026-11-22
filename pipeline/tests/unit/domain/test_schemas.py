from __future__ import annotations

from pipeline.tests.paths import PROJECT_ROOT
import sys
from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

from internnexus_core.jobs import JobSource as CoreJobSource
from internnexus_core.jobs import JobType as CoreJobType
from internnexus_core.jobs import WorkMode as CoreWorkMode

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.domain import JobSchema
from pipeline.domain.schemas import JobSource as DomainJobSource
from pipeline.domain.schemas import JobType as DomainJobType
from pipeline.domain.schemas import WorkMode as DomainWorkMode
from pipeline.infra.models import JobSource as OrmJobSource


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


@pytest.mark.parametrize("apply_url", ["", "   "])
def test_job_schema_rejects_empty_apply_url(apply_url: str) -> None:
    with pytest.raises(ValidationError, match="apply_url must not be empty"):
        JobSchema(
            source="greenhouse",
            title="Software Engineer",
            company="Acme",
            location="Remote",
            apply_url=apply_url,
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


@pytest.mark.parametrize(
    ("domain_literal", "core_enum", "expected_size"),
    [
        (DomainJobSource, CoreJobSource, 4),
        (DomainJobType, CoreJobType, 3),
        (DomainWorkMode, CoreWorkMode, 3),
    ],
    ids=["JobSource", "JobType", "WorkMode"],
)
def test_domain_literals_match_core_enum(domain_literal, core_enum, expected_size) -> None:
    literal_values = set(get_args(domain_literal))
    assert literal_values == {m.value for m in core_enum}
    assert len(literal_values) == len(core_enum) == expected_size
