"""Tests for stable shared job identity."""

import pytest

from internnexus_core.identity import fingerprint_for


def test_fingerprint_normalizes_surrounding_whitespace() -> None:
    assert fingerprint_for(" https://example.com/job/1 ") == fingerprint_for(
        "https://example.com/job/1"
    )


@pytest.mark.parametrize("apply_url", ["", "   "])
def test_fingerprint_rejects_empty_apply_url(apply_url: str) -> None:
    with pytest.raises(ValueError, match="apply_url must not be empty"):
        fingerprint_for(apply_url)
