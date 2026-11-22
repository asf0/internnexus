"""Location service for fetching and building location hierarchies."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job

# Facet budget: the toolbar only renders a handful of entries per level.
_MIN_CITY_COUNT = 10
_MIN_STATE_COUNT = 5
_MAX_CITIES = 200


class LocationService:
    """Service for location-related operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_location_hierarchy_from_filtered_jobs(self, filtered_jobs_stmt) -> list[dict]:
        """Get hierarchical locations from a pre-filtered jobs statement.

        One grouped query over the leaf ``(country, state, city)`` combinations
        replaces three separate grouping queries. The previous form executed
        the same filtered subquery three times -- once each for country, state,
        and city -- so a facet cache miss cost three full scans of the posting
        window. Country and state totals are summed from the leaf groups in
        Python, which is cheap compared with the extra scans.
        """
        subq = (
            filtered_jobs_stmt.order_by(None)
            .with_only_columns(
                Job.country,
                Job.state,
                Job.city,
                maintain_column_froms=True,
            )
            .subquery()
        )
        result = await self.session.execute(
            select(
                subq.c.country,
                subq.c.state,
                subq.c.city,
                func.count().label("job_count"),
            )
            .where(subq.c.country.isnot(None))
            .group_by(subq.c.country, subq.c.state, subq.c.city)
        )
        return self._build_hierarchy(result.all())

    def _build_hierarchy(self, rows: Iterable[Any]) -> list[dict]:
        """Build the country -> state -> city hierarchy from leaf counts."""
        country_counts: Counter[str] = Counter()
        state_counts: Counter[tuple[str, str]] = Counter()
        city_counts: Counter[tuple[str, str | None, str]] = Counter()

        for row in rows:
            country = row.country
            if not country:
                continue
            count = int(row.job_count or 0)
            if count <= 0:
                continue
            country_counts[country] += count
            if row.state:
                state_counts[(country, row.state)] += count
            if row.city:
                city_counts[(country, row.state, row.city)] += count

        cities_by_state: dict[tuple[str, str], list[dict]] = {}
        cities_without_state: dict[str, list[dict]] = {}
        # Keep the response bounded to the largest city groups. Sorting before
        # the cap makes the slice deterministic; the old unordered LIMIT could
        # drop large cities arbitrarily.
        top_cities = sorted(
            ((key, count) for key, count in city_counts.items() if count >= _MIN_CITY_COUNT),
            key=lambda item: (-item[1], item[0][2]),
        )[:_MAX_CITIES]
        for (country, state, city), count in top_cities:
            city_entry = {
                "value": city,
                "label": city,
                "count": count,
                "type": "city",
                "country": country,
                "state": state,
            }
            if state:
                cities_by_state.setdefault((country, state), []).append(city_entry)
            else:
                cities_without_state.setdefault(country, []).append(city_entry)

        for entries in (*cities_by_state.values(), *cities_without_state.values()):
            entries.sort(key=lambda entry: entry["label"])

        states_by_country: dict[str, list[dict]] = {}
        for (country, state), count in state_counts.items():
            if count < _MIN_STATE_COUNT:
                continue
            states_by_country.setdefault(country, []).append(
                {
                    "value": state,
                    "label": state,
                    "count": count,
                    "type": "state",
                    "country": country,
                    "children": cities_by_state.get((country, state), []),
                }
            )

        for entries in states_by_country.values():
            entries.sort(key=lambda entry: entry["label"])

        locations: list[dict] = []
        for country, count in country_counts.items():
            state_children = states_by_country.get(country, [])
            city_children = cities_without_state.get(country, [])
            locations.append(
                {
                    "value": country,
                    "label": country,
                    "count": count,
                    "type": "country",
                    "children": state_children if state_children else city_children,
                }
            )

        locations.sort(key=lambda entry: entry["label"])
        return locations
