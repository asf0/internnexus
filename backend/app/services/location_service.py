"""Location service for fetching and building location hierarchies."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job


class LocationService:
    """Service for location-related operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_location_hierarchy(self) -> list[dict]:
        """Get all distinct locations with hierarchical structure.

        Returns a list of countries, each containing states (if any),
        and each state containing cities.

        Returns:
            List of country dictionaries with nested state/city structure
        """
        countries = await self._fetch_countries()
        states = await self._fetch_states()
        cities = await self._fetch_cities()
        return self._build_hierarchy(countries, states, cities)

    async def get_location_hierarchy_from_filtered_jobs(self, filtered_jobs_stmt) -> list[dict]:
        """Get hierarchical locations from a pre-filtered jobs statement."""
        subq = filtered_jobs_stmt.subquery()
        countries = await self._fetch_countries_from_subquery(subq)
        states = await self._fetch_states_from_subquery(subq)
        cities = await self._fetch_cities_from_subquery(subq)
        return self._build_hierarchy(countries, states, cities)

    async def _fetch_countries(self) -> list[tuple[str, int]]:
        """Fetch countries with job counts.

        Returns:
            List of (country_name, job_count) tuples
        """
        result = await self.session.execute(
            select(Job.country, func.count(Job.id).label("job_count"))
            .where(Job.country.isnot(None))
            .group_by(Job.country)
        )
        return [(row.country, row.job_count) for row in result.all()]

    async def _fetch_countries_from_subquery(self, subq) -> list[tuple[str, int]]:
        """Fetch countries with counts from a filtered jobs subquery."""
        result = await self.session.execute(
            select(subq.c.country, func.count(subq.c.id).label("job_count"))
            .where(subq.c.country.isnot(None))
            .group_by(subq.c.country)
        )
        return [(row.country, row.job_count) for row in result.all()]

    async def _fetch_states(self) -> list[tuple[str, str, int]]:
        """Fetch states with country and job counts.

        Returns:
            List of (state_name, country, job_count) tuples
        """
        result = await self.session.execute(
            select(Job.state, Job.country, func.count(Job.id).label("job_count"))
            .where(Job.state.isnot(None))
            .group_by(Job.state, Job.country)
        )
        return [(row.state, row.country, row.job_count) for row in result.all()]

    async def _fetch_states_from_subquery(self, subq) -> list[tuple[str, str, int]]:
        """Fetch states with country and counts from a filtered jobs subquery."""
        result = await self.session.execute(
            select(subq.c.state, subq.c.country, func.count(subq.c.id).label("job_count"))
            .where(subq.c.state.isnot(None))
            .group_by(subq.c.state, subq.c.country)
        )
        return [(row.state, row.country, row.job_count) for row in result.all()]

    async def _fetch_cities(self) -> list[tuple[str, str | None, str, int]]:
        """Fetch cities with state, country, and job counts.

        Returns:
            List of (city_name, state, country, job_count) tuples
        """
        result = await self.session.execute(
            select(Job.city, Job.state, Job.country, func.count(Job.id).label("job_count"))
            .where(Job.city.isnot(None))
            .group_by(Job.city, Job.state, Job.country)
            .limit(200)
        )
        return [(row.city, row.state, row.country, row.job_count) for row in result.all()]

    async def _fetch_cities_from_subquery(self, subq) -> list[tuple[str, str | None, str, int]]:
        """Fetch cities with state/country and counts from a filtered jobs subquery."""
        result = await self.session.execute(
            select(
                subq.c.city,
                subq.c.state,
                subq.c.country,
                func.count(subq.c.id).label("job_count"),
            )
            .where(subq.c.city.isnot(None))
            .group_by(subq.c.city, subq.c.state, subq.c.country)
            .limit(200)
        )
        return [(row.city, row.state, row.country, row.job_count) for row in result.all()]

    def _build_hierarchy(
        self,
        countries: list[tuple[str, int]],
        states: list[tuple[str, str, int]],
        cities: list[tuple[str, str | None, str, int]],
    ) -> list[dict]:
        """Build hierarchical location structure from raw data.

        Args:
            countries: List of (country, count) tuples
            states: List of (state, country, count) tuples
            cities: List of (city, state, country, count) tuples

        Returns:
            List of country dictionaries with nested children
        """
        # Build city lookup by state and country
        cities_by_state = self._group_cities_by_state(cities)
        cities_by_country_no_state = self._group_cities_without_state(cities)

        # Build state lookup by country
        states_by_country = self._build_states_with_cities(states, cities_by_state)

        # Build final country list
        return self._build_country_list(countries, states_by_country, cities_by_country_no_state)

    def _group_cities_by_state(
        self, cities: list[tuple[str, str | None, str, int]]
    ) -> dict[str, list[dict]]:
        """Group cities by their state key (state|country).

        Args:
            cities: List of city tuples

        Returns:
            Dictionary mapping state_key to list of city entries
        """
        cities_by_state: dict[str, list[dict]] = {}

        for city, state, country, count in cities:
            if count is None or count < 10:
                continue

            city_entry = {
                "value": city,
                "label": city,
                "count": count,
                "type": "city",
                "country": country,
                "state": state,
            }

            if state:
                state_key = f"{state}|{country}"
                if state_key not in cities_by_state:
                    cities_by_state[state_key] = []
                cities_by_state[state_key].append(city_entry)

        # Sort cities within each state
        for state_key in cities_by_state:
            cities_by_state[state_key].sort(key=lambda x: x["label"])

        return cities_by_state

    def _group_cities_without_state(
        self, cities: list[tuple[str, str | None, str, int]]
    ) -> dict[str, list[dict]]:
        """Group cities that have no state by their country.

        Args:
            cities: List of city tuples

        Returns:
            Dictionary mapping country to list of city entries
        """
        cities_by_country: dict[str, list[dict]] = {}

        for city, state, country, count in cities:
            if count is None or count < 10:
                continue

            if not state:  # Only cities without state
                city_entry = {
                    "value": city,
                    "label": city,
                    "count": count,
                    "type": "city",
                    "country": country,
                    "state": state,
                }

                if country not in cities_by_country:
                    cities_by_country[country] = []
                cities_by_country[country].append(city_entry)

        # Sort cities within each country
        for country in cities_by_country:
            cities_by_country[country].sort(key=lambda x: x["label"])

        return cities_by_country

    def _build_states_with_cities(
        self,
        states: list[tuple[str, str, int]],
        cities_by_state: dict[str, list[dict]],
    ) -> dict[str, list[dict]]:
        """Build state entries with their nested cities.

        Args:
            states: List of state tuples
            cities_by_state: Dictionary of cities grouped by state

        Returns:
            Dictionary mapping country to list of state entries
        """
        states_by_country: dict[str, list[dict]] = {}

        for state, country, count in states:
            if count is None or count < 5:
                continue

            state_key = f"{state}|{country}"
            state_entry = {
                "value": state,
                "label": state,
                "count": count,
                "type": "state",
                "country": country,
                "children": cities_by_state.get(state_key, []),
            }

            if country not in states_by_country:
                states_by_country[country] = []
            states_by_country[country].append(state_entry)

        # Sort states within each country
        for country in states_by_country:
            states_by_country[country].sort(key=lambda x: x["label"])

        return states_by_country

    def _build_country_list(
        self,
        countries: list[tuple[str, int]],
        states_by_country: dict[str, list[dict]],
        cities_by_country: dict[str, list[dict]],
    ) -> list[dict]:
        """Build final sorted list of country entries.

        Args:
            countries: List of country tuples
            states_by_country: Dictionary of states grouped by country
            cities_by_country: Dictionary of cities without states by country

        Returns:
            Sorted list of country dictionaries
        """
        locations: list[dict] = []

        for country, count in countries:
            state_children = states_by_country.get(country, [])
            city_children = cities_by_country.get(country, [])

            country_entry: dict = {
                "value": country,
                "label": country,
                "count": count,
                "type": "country",
                "children": state_children if state_children else city_children,
            }
            locations.append(country_entry)

        # Sort countries alphabetically
        locations.sort(key=lambda x: x["label"])

        return locations
