"""Post-ranking filters applied to cached match results."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.schemas.matching import MatchResult
from app.services.jobs.posted_within import DEFAULT_JOB_POSTED_WITHIN_DAYS, posted_within_cutoff
from app.services.jobs.query_parser import split_pipe_values

def parse_filter_values(filter_value: str | None) -> list[str]:
    """Parse pipe-separated filter values into a list.

    Args:
        filter_value: Raw filter value from query parameter (may contain | delimiters)

    Returns:
        List of individual filter values, empty list if no valid values
    """
    return split_pipe_values(filter_value, drop_empty=True)


def filter_matches(
    matches: list[MatchResult],
    search: str | None = None,
    company: str | None = None,
    location: str | None = None,
    category: str | None = None,
    job_type: str | None = None,
    work_mode: str | None = None,
    posted_within: str | None = None,
) -> list[MatchResult]:
    """Filter match results based on provided criteria.

    Supports multiple values for filters (separated by |), using OR logic.
    For example, location="United States|Brazil" will match jobs in either location.
    """
    filtered = matches

    if search:
        search_lower = search.lower()
        filtered = [
            m
            for m in filtered
            if (
                search_lower in m.title.lower()
                or search_lower in m.company.lower()
                # Cached match results deliberately retain only sanitized
                # description HTML, never the raw job description text.
                or search_lower in m.description_html.lower()
            )
        ]

    # Company filter with multiple values (OR logic)
    if company:
        company_values = parse_filter_values(company)
        if company_values:
            company_values_lower = [v.lower() for v in company_values]
            filtered = [m for m in filtered if any(v in m.company.lower() for v in company_values_lower)]

    # Location filter with multiple values (OR logic)
    if location:
        location_values = parse_filter_values(location)
        if location_values:
            location_values_lower = [v.lower() for v in location_values]
            filtered = [
                m
                for m in filtered
                if any(
                    v in m.location.lower()
                    or (m.city and v in m.city.lower())
                    or (m.state and v in m.state.lower())
                    or (m.country and v in m.country.lower())
                    for v in location_values_lower
                )
            ]

    # Category filter with multiple values (OR logic)
    if category:
        category_values = parse_filter_values(category)
        if category_values:
            category_values_lower = [v.lower() for v in category_values]
            filtered = [
                m
                for m in filtered
                if m.job_category and any(v in m.job_category.lower() for v in category_values_lower)
            ]

    # Job type filter with multiple values (OR logic)
    if job_type:
        job_type_values = parse_filter_values(job_type)
        if job_type_values:
            job_type_values_lower = [v.lower() for v in job_type_values]
            filtered = [
                m for m in filtered if m.job_type and any(v in m.job_type.lower() for v in job_type_values_lower)
            ]

    # Work mode filter with multiple values (OR logic)
    if work_mode:
        work_mode_values = parse_filter_values(work_mode)
        if work_mode_values:
            work_mode_values_lower = [v.lower() for v in work_mode_values]
            filtered = [
                m for m in filtered if m.work_mode and any(v in m.work_mode.lower() for v in work_mode_values_lower)
            ]

    if posted_within:
        cutoff = posted_within_cutoff(posted_within, datetime.now(timezone.utc))
        if cutoff:
            filtered = [m for m in filtered if m.posted_at and m.posted_at >= cutoff]
    else:
        filtered = apply_default_recency_filter(filtered)

    return filtered


def apply_default_recency_filter(matches: list[MatchResult]) -> list[MatchResult]:
    """Filter out matches older than DEFAULT_JOB_POSTED_WITHIN_DAYS.

    Jobs with no posted_at date are retained (recency_score defaults to 0.4 for them).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=DEFAULT_JOB_POSTED_WITHIN_DAYS)
    return [m for m in matches if m.posted_at is None or m.posted_at >= cutoff]
