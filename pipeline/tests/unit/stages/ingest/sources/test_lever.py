"""Unit tests for the Lever adapter."""

from __future__ import annotations

from pipeline.stages.ingest.sources.lever import LeverClient


def test_lever_normalizer_populates_posted_at_from_created_at() -> None:
    client = object.__new__(LeverClient)
    created_at = 1_700_000_000_000  # ms timestamp

    jobs = client._normalize_jobs(
        "example",
        [
            {
                "id": "job-1",
                "text": "Software Engineer Intern",
                "categories": {"location": "Remote"},
                "applyUrl": "https://jobs.lever.co/example/job-1",
                "description": "A sufficiently long internship description.",
                "createdAt": created_at,
            }
        ],
    )

    assert len(jobs) == 1
    assert jobs[0].posted_at is not None
    assert jobs[0].posted_at.year == 2023
    assert jobs[0].source == "lever"
    assert jobs[0].company == "example"
