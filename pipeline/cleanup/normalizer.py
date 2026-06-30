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


def _rowcount(result: object) -> int:
    raw = getattr(result, "rowcount", 0)
    return int(raw or 0)


async def _normalize_existing_states(session: AsyncSession) -> int:
    total_updated = 0

    for column in ("state", "city", "country"):
        result = await session.execute(
            text(
                f"UPDATE jobs SET {column} = TRIM({column}) "
                f"WHERE {column} IS NOT NULL AND {column} IS DISTINCT FROM TRIM({column})"
            )
        )
        total_updated += _rowcount(result)

    for state, country in COUNTRIES_AS_STATES.items():
        result = await session.execute(
            text("UPDATE jobs SET country = :country, state = NULL WHERE state = :state"),
            {"country": country, "state": state},
        )
        total_updated += _rowcount(result)

    result = await session.execute(
        text("UPDATE jobs SET state = NULL WHERE state = ANY(:cities)"),
        {"cities": list(CITIES_AS_STATES.keys())},
    )
    total_updated += _rowcount(result)

    result = await session.execute(
        text("UPDATE jobs SET state = NULL WHERE state = ANY(:invalid)"),
        {"invalid": list(INVALID_STATES)},
    )
    total_updated += _rowcount(result)

    state_mappings_with_values = {k: v for k, v in STATE_MAPPINGS.items() if v is not None}
    state_mappings_null = [k for k, v in STATE_MAPPINGS.items() if v is None]

    if state_mappings_with_values:
        for old_state, new_state in state_mappings_with_values.items():
            result = await session.execute(
                text("UPDATE jobs SET state = :new_state WHERE state = :old_state"),
                {"new_state": new_state, "old_state": old_state},
            )
            total_updated += _rowcount(result)

    if state_mappings_null:
        result = await session.execute(
            text("UPDATE jobs SET state = NULL WHERE state = ANY(:null_states)"),
            {"null_states": state_mappings_null},
        )
        total_updated += _rowcount(result)

    lower_countries = [c.lower() for c in COUNTRIES_AS_CITIES]
    result = await session.execute(
        text("UPDATE jobs SET city = NULL WHERE LOWER(city) = ANY(:countries)"),
        {"countries": lower_countries},
    )
    total_updated += _rowcount(result)

    lower_states = [s.lower() for s in STATES_AS_CITIES]
    result = await session.execute(
        text("UPDATE jobs SET city = NULL WHERE LOWER(city) = ANY(:states)"),
        {"states": lower_states},
    )
    total_updated += _rowcount(result)

    combined_pattern = "|".join(INVALID_CITY_PATTERN_STRINGS)
    result = await session.execute(
        text("UPDATE jobs SET city = NULL WHERE city ~* :pattern"),
        {"pattern": combined_pattern},
    )
    total_updated += _rowcount(result)

    await session.commit()
    return total_updated
