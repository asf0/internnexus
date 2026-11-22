"""Shared helpers used by the ATS source adapters."""

from __future__ import annotations

from pipeline.stages.ingest.sources.utils import parse_unix_timestamp


def test_parse_unix_timestamp_returns_timezone_aware_utc():
    parsed = parse_unix_timestamp(0)
    assert parsed is None

    parsed = parse_unix_timestamp(1_700_000_000_000)
    assert parsed is not None
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0
