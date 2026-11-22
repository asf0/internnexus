"""Facet counts and the country/state/city hierarchy for a match session."""

from __future__ import annotations

from app.schemas.matching import FacetItem, LocationFacetItem, MatchFacetsResponse, MatchResult

def calculate_facets(matches: list[MatchResult]) -> MatchFacetsResponse:
    """Calculate facet values and counts from a list of matches.

    Args:
        matches: List of MatchResult objects to analyze

    Returns:
        MatchFacetsResponse with companies, categories, job_types, work_modes, and locations
    """
    # Count companies
    company_counts: dict[str, int] = {}
    for match in matches:
        company = match.company
        company_counts[company] = company_counts.get(company, 0) + 1

    companies = [
        FacetItem(value=company, label=company, count=count)
        for company, count in sorted(company_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    # Count categories
    category_counts: dict[str, int] = {}
    for match in matches:
        if match.job_category:
            category_counts[match.job_category] = category_counts.get(match.job_category, 0) + 1

    categories = [
        FacetItem(value=cat, label=cat, count=count)
        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    # Count job types
    job_type_counts: dict[str, int] = {}
    for match in matches:
        if match.job_type:
            job_type_counts[match.job_type] = job_type_counts.get(match.job_type, 0) + 1

    job_types = [
        FacetItem(value=jt, label=jt, count=count)
        for jt, count in sorted(job_type_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    # Count work modes
    work_mode_counts: dict[str, int] = {}
    for match in matches:
        if match.work_mode:
            work_mode_counts[match.work_mode] = work_mode_counts.get(match.work_mode, 0) + 1

    work_modes = [
        FacetItem(value=wm, label=wm, count=count)
        for wm, count in sorted(work_mode_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    # Build location hierarchy
    locations = build_location_hierarchy(matches)

    return MatchFacetsResponse(
        companies=companies,
        categories=categories,
        job_types=job_types,
        work_modes=work_modes,
        locations=locations,
        total_matches=len(matches),
    )


def build_location_hierarchy(matches: list[MatchResult]) -> list[LocationFacetItem]:
    """Build location hierarchy from match location data.

    Args:
        matches: List of MatchResult objects

    Returns:
        Hierarchical list of LocationFacetItem objects
    """
    # Track counts per location path
    country_counts: dict[str, int] = {}
    state_counts: dict[tuple[str, str], int] = {}  # (country, state) -> count
    city_counts: dict[tuple[str, str | None, str], int] = {}  # (country, state, city) -> count

    for match in matches:
        country = match.country
        state = match.state
        city = match.city

        if country:
            country_counts[country] = country_counts.get(country, 0) + 1

        if country and state:
            state_key = (country, state)
            state_counts[state_key] = state_counts.get(state_key, 0) + 1

        if country and city:
            city_key = (country, state, city)
            city_counts[city_key] = city_counts.get(city_key, 0) + 1

    # Build hierarchy
    locations: list[LocationFacetItem] = []

    for country, country_count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True):
        # Get states for this country
        country_states = [(state, count) for (c, state), count in state_counts.items() if c == country]

        state_items: list[LocationFacetItem] = []
        for state, state_count in sorted(country_states, key=lambda x: x[1], reverse=True):
            # Get cities for this state
            state_cities = [(city, count) for (c, s, city), count in city_counts.items() if c == country and s == state]

            city_items: list[LocationFacetItem] = []
            for city, city_count in sorted(state_cities, key=lambda x: x[1], reverse=True):
                city_items.append(
                    LocationFacetItem(
                        value=city,
                        label=city,
                        count=city_count,
                        type="city",
                        country=country,
                        state=state,
                        children=None,
                    )
                )

            state_items.append(
                LocationFacetItem(
                    value=state,
                    label=state,
                    count=state_count,
                    type="state",
                    country=country,
                    state=state,
                    children=city_items if city_items else None,
                )
            )

        locations.append(
            LocationFacetItem(
                value=country,
                label=country,
                count=country_count,
                type="country",
                country=country,
                state=None,
                children=state_items if state_items else None,
            )
        )

    return locations
