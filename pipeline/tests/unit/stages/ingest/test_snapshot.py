from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pipeline.domain import JobSchema
from pipeline.domain.job_identity import fingerprint_for
from pipeline.domain.board_snapshot import (
    build_board_snapshot,
    canonical_job_payload,
    job_content_hash,
)


def _job(**overrides) -> JobSchema:
    values = {
        "source": "greenhouse",
        "title": "Software Engineer Intern",
        "company": "Example",
        "location": "Remote",
        "apply_url": "https://example.com/jobs/1",
        "description_text": "Build useful things.",
        "posted_at": datetime(2026, 7, 12, 18, 30, tzinfo=timezone.utc),
        "job_type": "internship",
        "work_mode": "remote",
    }
    values.update(overrides)
    return JobSchema(**values)


@pytest.mark.parametrize(
    ("field", "changed_value"),
    [
        ("title", "Platform Engineer Intern"),
        ("company", "Another Company"),
        ("location", "Denver, CO"),
        ("apply_url", "https://example.com/jobs/2"),
        ("description_text", "Build different things."),
        ("posted_at", datetime(2026, 7, 13, 18, 30, tzinfo=timezone.utc)),
        ("job_type", "full_time"),
        ("work_mode", "hybrid"),
    ],
)
def test_job_hash_changes_for_each_persisted_source_field(field, changed_value) -> None:
    original = _job()
    changed = _job(**{field: changed_value})

    assert job_content_hash(original) != job_content_hash(changed)


def test_job_hash_excludes_downstream_derived_fields() -> None:
    original = _job()
    enriched = _job(
        city="Denver",
        state="CO",
        country="US",
        job_category="Software Engineering",
        description_embedding=[0.1, 0.2, 0.3],
    )

    assert job_content_hash(original) == job_content_hash(enriched)


def test_job_hash_uses_cleaned_persisted_text() -> None:
    raw = _job(
        title="Software\x00 Engineer Intern",
        description_text='<p style="color:red">Build &amp; learn.\x00</p>',
    )
    cleaned = _job(
        title="Software Engineer Intern",
        description_text="<p>Build & learn.</p>",
    )

    assert canonical_job_payload(raw) == canonical_job_payload(cleaned)
    assert job_content_hash(raw) == job_content_hash(cleaned)


def test_job_hash_normalizes_equivalent_timezone_representations() -> None:
    utc = _job(posted_at=datetime(2026, 7, 12, 18, 30, tzinfo=timezone.utc))
    mountain = _job(
        posted_at=datetime(
            2026,
            7,
            12,
            12,
            30,
            tzinfo=timezone(-timedelta(hours=6)),
        )
    )
    naive_utc = _job(posted_at=datetime(2026, 7, 12, 18, 30))

    assert job_content_hash(utc) == job_content_hash(mountain)
    assert job_content_hash(utc) == job_content_hash(naive_utc)


def test_board_snapshot_is_independent_of_job_order() -> None:
    first = _job()
    second = _job(
        apply_url="https://example.com/jobs/2",
        title="Data Engineer Intern",
    )

    forward = build_board_snapshot([first, second])
    reverse = build_board_snapshot([second, first])

    assert forward.board_hash == reverse.board_hash
    assert forward.manifest == reverse.manifest
    assert list(forward.manifest) == sorted(forward.manifest)


def test_board_snapshot_deduplicates_identical_fingerprints() -> None:
    job = _job()

    snapshot = build_board_snapshot([job, job.model_copy(deep=True)])

    assert snapshot.job_count == 1
    assert snapshot.manifest == {fingerprint_for(job): job_content_hash(job)}


def test_conflicting_duplicates_are_resolved_deterministically() -> None:
    first = _job(title="A title")
    second = _job(title="B title")

    forward = build_board_snapshot([first, second])
    reverse = build_board_snapshot([second, first])

    assert forward.board_hash == reverse.board_hash
    assert forward.manifest == reverse.manifest
    assert forward.jobs_by_fingerprint[fingerprint_for(first)].title == "A title"


def test_empty_board_has_a_stable_sha256_snapshot() -> None:
    first = build_board_snapshot([])
    second = build_board_snapshot([])

    assert first == second
    assert first.job_count == 0
    assert len(first.board_hash) == 64
