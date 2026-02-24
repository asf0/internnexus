"""Metadata fetching for cleanup module."""

from __future__ import annotations

from uuid import UUID

from pipeline.repositories.sqlalchemy_repo import SQLAlchemyJobRepository
from pipeline.location.simple_parser import (
    normalize_location,
    normalize_state_name,
    clean_city_name,
)


async def _fetch_jobs_chunk(
    repo: SQLAlchemyJobRepository,
    since,
    process_all,
    last_id: UUID | None,
    chunk_size: int,
):
    jobs = await repo.fetch_jobs_batch_keyset(
        since=since,
        process_all=process_all,
        last_id=last_id,
        limit=chunk_size,
    )
    if not jobs:
        return [], {}, {}, {}

    metadata_batch = await repo.fetch_metadata_batch([job.id for job in jobs])

    rows = []
    for job in jobs:
        rows.append(
            {
                "id": job.id,
                "source": job.source,
                "location": job.location,
                "city": job.city,
                "state": job.state,
                "country": job.country,
            }
        )

    return rows, metadata_batch.ashby, metadata_batch.greenhouse, metadata_batch.lever


def _get_metadata_result(
    row, ashby_map: dict, greenhouse_map: dict, lever_map: dict
) -> tuple[dict | None, str]:
    job_id = row["id"]
    source = str(row["source"]).lower()

    if source == "ashby" and job_id in ashby_map:
        ashby = ashby_map[job_id]
        if (
            ashby.get("address_locality")
            and ashby.get("address_region")
            and ashby.get("address_country")
        ):
            addr_country = ashby["address_country"]
            if addr_country.upper() == "USA":
                addr_country = "United States"
            raw_location = f"{ashby['address_locality']}, {ashby['address_region']}, {addr_country}"
            parsed = normalize_location(raw_location)
            raw_state = parsed.get("state") or ashby["address_region"]
            normalized_state = normalize_state_name(raw_state) if raw_state else None
            raw_city = parsed.get("city") or ashby["address_locality"]
            normalized_city = clean_city_name(raw_city) if raw_city else None
            return {
                "city": normalized_city,
                "state": normalized_state,
                "country": parsed.get("country") or addr_country,
            }, "ashby_metadata"

    if source == "greenhouse" and job_id in greenhouse_map:
        gh = greenhouse_map[job_id]
        offices = gh.get("offices") or []
        for office in offices:
            office_loc = office.get("location")
            office_name = office.get("name", "").strip()

            if not office_loc or not office_loc.strip():
                skip_patterns = (
                    "US",
                    "UK",
                    "EU",
                    "APAC",
                    "EMEA",
                    "North America",
                    "South America",
                    "Canada Locations",
                    "LT - North America",
                )
                if office_name.upper() in skip_patterns:
                    continue
                if "remote" in office_name.lower():
                    office_loc = office_name
                elif len(office_name) > 2 and "," not in office_name and len(office_name) < 30:
                    office_loc = office_name

            if office_loc and office_loc.strip():
                parsed = normalize_location(office_loc)
                if parsed.get("city") or parsed.get("country") or parsed.get("full") == "Remote":
                    raw_state = parsed.get("state")
                    normalized_state = normalize_state_name(raw_state) if raw_state else None
                    raw_city = parsed.get("city")
                    normalized_city = clean_city_name(raw_city) if raw_city else None
                    return {
                        "city": normalized_city,
                        "state": normalized_state,
                        "country": parsed.get("country"),
                    }, "greenhouse_metadata"

    if source == "lever" and job_id in lever_map:
        lev = lever_map[job_id]
        all_locs = lev.get("all_locations") or []
        if all_locs and all_locs[0]:
            parsed = normalize_location(all_locs[0])
            if parsed.get("city") or parsed.get("country"):
                raw_state = parsed.get("state")
                normalized_state = normalize_state_name(raw_state) if raw_state else None
                raw_city = parsed.get("city")
                normalized_city = clean_city_name(raw_city) if raw_city else None
                return {
                    "city": normalized_city,
                    "state": normalized_state,
                    "country": parsed.get("country"),
                }, "lever_metadata"

    return None, "fallback"


def _merge_location_results(
    location_str: str, parsed_result: dict, metadata_result: dict | None, metadata_source: str
) -> tuple[dict, str]:
    from pipeline.cleanup.parser import _is_plain_remote

    if _is_plain_remote(location_str):
        return {
            "city": None,
            "state": None,
            "country": None,
        }, "location_string"

    if parsed_result.get("city") or parsed_result.get("country"):
        from pipeline.cleanup.parser import _is_metadata_consistent

        if metadata_result and _is_metadata_consistent(
            location_str, parsed_result, metadata_result
        ):
            raw_state = parsed_result.get("state") or metadata_result.get("state")
            normalized_state = normalize_state_name(raw_state) if raw_state else None
            merged = {
                "city": parsed_result.get("city") or metadata_result.get("city"),
                "state": normalized_state,
                "country": parsed_result.get("country") or metadata_result.get("country"),
            }
            return merged, metadata_source

        return parsed_result, "location_string"

    if metadata_result:
        from pipeline.cleanup.parser import _is_metadata_consistent

        if _is_metadata_consistent(location_str, parsed_result, metadata_result):
            raw_state = metadata_result.get("state")
            if raw_state:
                metadata_result = {
                    **metadata_result,
                    "state": normalize_state_name(raw_state),
                }
            return metadata_result, metadata_source

    return parsed_result, "location_string"
