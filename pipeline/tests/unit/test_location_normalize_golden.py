"""Golden fixture tests for pipeline.location.simple_parser.normalize_location.

Captures current output across ~100 representative inputs so any refactor
can be verified against this behavior-preserving safety net.

Generator: uv run pytest --generate-location-fixture
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pipeline.location.simple_parser import normalize_location

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures"
FIXTURE_PATH = FIXTURE_DIR / "location_normalize_cases.json"


def load_golden_cases() -> list[dict]:
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["cases"]


def _generate_fixture() -> None:
    inputs = [
        "London",
        "Tokyo",
        "Vancouver",
        "Birmingham",
        "Berlin",
        "Mumbai",
        "Singapore",
        "Paris",
        "Sydney",
        "Dubai",
        "Seoul",
        "Istanbul",
        "Austin, TX",
        "New York, NY",
        "Toronto, ON",
        "San Francisco, CA",
        "Bangalore, KA",
        "Sydney, NSW",
        "Los Angeles, CA",
        "Chicago, IL",
        "Austin, TX 78701",
        "Toronto, ON, Canada",
        "Munich, Bavaria, Germany",
        "Bangalore, KA, India",
        "Tokyo, Tokyo, Japan",
        "San Francisco, CA, US",
        "Paris, Ile-de-France, France",
        "London, UK",
        "123 Main St, Springfield, IL",
        "456 Oak Ave, Portland, OR",
        "1000 Broadway, Denver, CO",
        "789 Pine Rd, Austin, TX 78701",
        "Remote",
        "Remote - US",
        "Remote - Canada",
        "Hybrid",
        "Hybrid | London",
        "Remote - EMEA",
        "Virtual",
        "Work from home",
        "Remote; London",
        "NYC | Remote",
        "Austin, TX; Denver, CO",
        "London, UK; Paris, France",
        "Berlin, Germany; Tokyo, Japan; Sydney, Australia",
        "NY Metro",
        "New York Metro",
        "Various",
        "TBD",
        "Anywhere",
        "Multiple Locations",
        "N/A",
        "Unknown",
        "To Be Determined",
        "Virtual Location",
        "Office",
        "Hub",
        "Zone",
        "Region",
        "Area",
        "Building 1",
        "Room A",
        "Suite 5, London",
        "United States",
        "USA",
        "GB",
        "UK",
        "Canada",
        "Turkiye",
        "Czech Republic",
        "UAE",
        "France",
        "India",
        "US",
        "DE",
        "FR",
        "IN",
        "AE",
        "U.S.",
        "California",
        "Ontario",
        "Maharashtra",
        "Bavaria",
        "New South Wales",
        "Quebec",
        "Karnataka",
        "Texas",
        "Washington",
        "Georgia",
        "Delhi",
        "New York",
        "Victoria",
        "Virginia",
        None,
        "",
        " ",
        " , ",
        "Remote, Remote",
        ",,",
        "Paris City",
        "New York City",
        "Australia - Sydney",
        "India - Pune",
        "Germany, EMEA",
        "Remote - APAC",
        "US, AMER",
        "Global",
        "u.s.",
        "Türkiye",
        "United Arab Emirates",
        "South Korea",
        "Vancouver, WA",
        "Birmingham, AL",
        "123 Main Bldg Springfield",
    ]
    cases = []
    for inp in inputs:
        result = normalize_location(inp)
        cases.append({"input": inp, "expected": result})

    fixture = {
        "version": 2,
        "description": "outputs for pipeline.location.simple_parser.normalize_location, captured 2026-07-01.",
        "changelog": "Version 2: Corrected Vancouver (\u2192Canada) and Birmingham (\u2192UK) bare city resolution; added Vancouver, WA and Birmingham, AL state-qualified regression cases; added 123 Main Bldg Springfield case for bldg typo fix.",
        "cases": cases,
    }
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    with open(FIXTURE_PATH, "w", encoding="utf-8") as f:
        json.dump(fixture, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(cases)} golden cases to {FIXTURE_PATH}")


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "golden_case" in metafunc.fixturenames:
        cases = load_golden_cases()
        metafunc.parametrize(
            "golden_case",
            cases,
            ids=[str(c["input"]) for c in cases],
        )


def test_golden_normalize_location(golden_case: dict) -> None:
    inp = golden_case["input"]
    expected = golden_case["expected"]
    assert normalize_location(inp) == expected


def test_fixture_schema() -> None:
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert data["version"] == 2
    assert isinstance(data["description"], str)
    assert len(data["description"]) > 0
    cases = data["cases"]
    assert 80 <= len(cases) <= 120, f"Expected 80-120 cases, got {len(cases)}"
    for c in cases:
        assert "input" in c
        assert "expected" in c
        exp = c["expected"]
        for key in ("full", "city", "state", "country", "all_cities", "is_remote", "is_multi_location"):
            assert key in exp, f"Missing key {key!r} in case {c['input']!r}"
        assert isinstance(exp["is_remote"], bool)
        assert isinstance(exp["is_multi_location"], bool)
