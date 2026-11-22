"""Unit tests for the single-query location hierarchy builder."""

from types import SimpleNamespace

from app.services.jobs.location import LocationService


def _row(country: str | None, state: str | None, city: str | None, count: int):
    return SimpleNamespace(country=country, state=state, city=city, job_count=count)


def _service() -> LocationService:
    return LocationService(session=None)  # type: ignore[arg-type]


def test_country_and_state_totals_are_summed_from_leaf_groups() -> None:
    locations = _service()._build_hierarchy(
        [
            _row("USA", "CA", "San Francisco", 20),
            _row("USA", "CA", "Los Angeles", 15),
            _row("USA", "NY", "New York", 8),
        ]
    )

    assert [entry["value"] for entry in locations] == ["USA"]
    usa = locations[0]
    assert usa["count"] == 43
    assert [entry["value"] for entry in usa["children"]] == ["CA", "NY"]
    ca = usa["children"][0]
    assert ca["count"] == 35
    assert [entry["value"] for entry in ca["children"]] == ["Los Angeles", "San Francisco"]


def test_small_city_and_state_groups_are_hidden() -> None:
    locations = _service()._build_hierarchy(
        [
            _row("USA", "CA", "Big City", 10),
            _row("USA", "CA", "Small City", 9),
            _row("USA", "WY", "Tiny", 4),
        ]
    )

    usa = locations[0]
    assert [entry["value"] for entry in usa["children"]] == ["CA"]
    assert [entry["value"] for entry in usa["children"][0]["children"]] == ["Big City"]


def test_cities_without_a_state_hang_off_the_country() -> None:
    locations = _service()._build_hierarchy(
        [
            _row("Brazil", None, "Sao Paulo", 12),
            _row("Brazil", None, "Rio de Janeiro", 11),
        ]
    )

    brazil = locations[0]
    assert brazil["children"] == [
        {"value": "Rio de Janeiro", "label": "Rio de Janeiro", "count": 11,
         "type": "city", "country": "Brazil", "state": None},
        {"value": "Sao Paulo", "label": "Sao Paulo", "count": 12,
         "type": "city", "country": "Brazil", "state": None},
    ]


def test_countries_and_children_are_sorted_by_label() -> None:
    locations = _service()._build_hierarchy(
        [
            _row("USA", "WA", "Seattle", 20),
            _row("Canada", "ON", "Toronto", 20),
            _row("USA", "CA", "San Francisco", 20),
        ]
    )

    assert [entry["value"] for entry in locations] == ["Canada", "USA"]
    assert [entry["value"] for entry in locations[1]["children"]] == ["CA", "WA"]


def test_null_country_rows_are_ignored() -> None:
    assert _service()._build_hierarchy([_row(None, "CA", "Somewhere", 50)]) == []
