"""Metadata fetching for cleanup module."""

from __future__ import annotations


def _get_metadata_result(row: dict) -> tuple[None, str]:
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
        return parsed_result, "location_string"

    return parsed_result, "location_string"
