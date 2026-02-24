"""State/country normalization for cleanup module."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.location.constants import (
    COUNTRIES_AS_STATES,
    CITIES_AS_STATES,
    INVALID_STATES,
    COUNTRIES_AS_CITIES,
    STATES_AS_CITIES,
    INVALID_CITY_PATTERN_STRINGS,
    STATE_MAPPINGS,
)


async def _normalize_existing_states(session: AsyncSession) -> int:
    total_updated = 0

    await session.execute(text("UPDATE jobs SET state = TRIM(state) WHERE state IS NOT NULL"))
    await session.execute(text("UPDATE jobs SET city = TRIM(city) WHERE city IS NOT NULL"))
    await session.execute(text("UPDATE jobs SET country = TRIM(country) WHERE country IS NOT NULL"))

    state_keys = list(COUNTRIES_AS_STATES.keys())
    case_clauses = " WHEN ".join(
        f"state = '{state}' THEN '{country}'" for state, country in COUNTRIES_AS_STATES.items()
    )
    case_clauses = f"CASE WHEN {case_clauses} END"
    result = await session.execute(
        text(f"""
            UPDATE jobs SET country = {case_clauses}, state = NULL
            WHERE state = ANY(:states)
        """),
        {"states": state_keys},
    )
    total_updated += result.rowcount or 0

    result = await session.execute(
        text("UPDATE jobs SET state = NULL WHERE state = ANY(:cities)"),
        {"cities": list(CITIES_AS_STATES.keys())},
    )
    total_updated += result.rowcount or 0

    result = await session.execute(
        text("UPDATE jobs SET state = NULL WHERE state = ANY(:invalid)"),
        {"invalid": list(INVALID_STATES)},
    )
    total_updated += result.rowcount or 0

    state_mappings_with_values = {k: v for k, v in STATE_MAPPINGS.items() if v is not None}
    state_mappings_null = [k for k, v in STATE_MAPPINGS.items() if v is None]

    if state_mappings_with_values:
        case_clauses = " WHEN ".join(
            f"state = '{state}' THEN '{new_state}'"
            for state, new_state in state_mappings_with_values.items()
        )
        case_clauses = f"CASE WHEN {case_clauses} END"
        result = await session.execute(
            text(f"""
                UPDATE jobs SET state = {case_clauses}
                WHERE state = ANY(:old_states)
            """),
            {"old_states": list(state_mappings_with_values.keys())},
        )
        total_updated += result.rowcount or 0

    if state_mappings_null:
        result = await session.execute(
            text("UPDATE jobs SET state = NULL WHERE state = ANY(:null_states)"),
            {"null_states": state_mappings_null},
        )
        total_updated += result.rowcount or 0

    lower_countries = [c.lower() for c in COUNTRIES_AS_CITIES]
    result = await session.execute(
        text("UPDATE jobs SET city = NULL WHERE LOWER(city) = ANY(:countries)"),
        {"countries": lower_countries},
    )
    total_updated += result.rowcount or 0

    lower_states = [s.lower() for s in STATES_AS_CITIES]
    result = await session.execute(
        text("UPDATE jobs SET city = NULL WHERE LOWER(city) = ANY(:states)"),
        {"states": lower_states},
    )
    total_updated += result.rowcount or 0

    combined_pattern = "|".join(INVALID_CITY_PATTERN_STRINGS)
    result = await session.execute(
        text("UPDATE jobs SET city = NULL WHERE city ~* :pattern"),
        {"pattern": combined_pattern},
    )
    total_updated += result.rowcount or 0

    await session.commit()
    return total_updated
