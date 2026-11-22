"""State/country normalization for cleanup module."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.dml import Update

from pipeline.stages.cleanup.location.constants import (
    COUNTRIES_AS_STATES,
    CITIES_AS_STATES,
    INVALID_STATES,
    COUNTRIES_AS_CITIES,
    STATES_AS_CITIES,
    INVALID_CITY_PATTERN_STRINGS,
    STATE_MAPPINGS,
)
from pipeline.infra.models import Job
from pipeline.repositories.job_text_sql import rowcount as _rowcount


def _statements(since: datetime | None) -> list[Update]:
    """Build the normalization statements, scoped to `last_seen >= since` when given.

    Statements are composed with SQLAlchemy Core (bound parameters only, no
    string interpolation) so identifiers can never be injected and the
    `since` scoping is applied uniformly.
    """

    def scoped(stmt: Update) -> Update:
        if since is not None:
            return stmt.execution_options(synchronize_session=False).where(Job.last_seen >= since)
        return stmt.execution_options(synchronize_session=False)

    statements: list[Update] = []

    for column in (Job.state, Job.city, Job.country):
        statements.append(
            scoped(
                update(Job)
                .where(column.isnot(None), column.is_distinct_from(func.trim(column)))
                .values({column.key: func.trim(column)})
            )
        )

    for state, country in COUNTRIES_AS_STATES.items():
        statements.append(
            scoped(update(Job).where(Job.state == state).values(country=country, state=None))
        )

    if CITIES_AS_STATES:
        statements.append(
            scoped(update(Job).where(Job.state.in_(list(CITIES_AS_STATES.keys()))).values(state=None))
        )

    if INVALID_STATES:
        statements.append(
            scoped(update(Job).where(Job.state.in_(list(INVALID_STATES))).values(state=None))
        )

    # Identity entries (e.g. "Quebec" -> "Quebec") would emit
    # `UPDATE jobs SET state = 'Quebec' WHERE state = 'Quebec'`, rewriting every
    # matching row to the value it already holds. That costs a new row version,
    # WAL, an idx_jobs_state update, and -- because `state` feeds search_vector --
    # a tsvector recompute plus GIN maintenance, all for no semantic change.
    # 24 of the 55 valued mappings are currently identities.
    state_mappings_with_values = {k: v for k, v in STATE_MAPPINGS.items() if v is not None and k != v}
    state_mappings_null = [k for k, v in STATE_MAPPINGS.items() if v is None]

    for old_state, new_state in state_mappings_with_values.items():
        statements.append(
            scoped(update(Job).where(Job.state == old_state).values(state=new_state))
        )

    if state_mappings_null:
        statements.append(
            scoped(update(Job).where(Job.state.in_(state_mappings_null)).values(state=None))
        )

    lower_countries = [c.lower() for c in COUNTRIES_AS_CITIES]
    if lower_countries:
        statements.append(
            scoped(update(Job).where(func.lower(Job.city).in_(lower_countries)).values(city=None))
        )

    lower_states = [s.lower() for s in STATES_AS_CITIES]
    if lower_states:
        statements.append(
            scoped(update(Job).where(func.lower(Job.city).in_(lower_states)).values(city=None))
        )

    if INVALID_CITY_PATTERN_STRINGS:
        combined_pattern = "|".join(INVALID_CITY_PATTERN_STRINGS)
        statements.append(
            scoped(update(Job).where(Job.city.op("~*")(combined_pattern)).values(city=None))
        )

    return statements


async def _normalize_existing_states(
    session: AsyncSession, since: datetime | None = None
) -> int:
    total_updated = 0
    for statement in _statements(since):
        result = await session.execute(statement)
        total_updated += _rowcount(result)

    await session.commit()
    return total_updated
