"""URL processing utilities."""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def add_utm_params(
    url: str,
    source: str = "internnexus",
    medium: str | None = None,
    campaign: str | None = None,
) -> str:
    """Add UTM tracking parameters to a URL.

    Preserves existing query parameters and handles fragments correctly.
    UTM parameters are sorted for consistency.

    Args:
        url: The URL to add UTM parameters to
        source: UTM source parameter (default: "internnexus")
        medium: UTM medium parameter (optional)
        campaign: UTM campaign parameter (optional)

    Returns:
        The URL with UTM parameters added

    Example:
        >>> add_utm_params("https://example.com/apply?ref=123", medium="web")
        'https://example.com/apply?ref=123&utm_medium=web&utm_source=internnexus'
    """
    parsed = urlparse(url)

    # Parse existing query parameters
    params: dict[str, list[str]] = parse_qs(parsed.query, keep_blank_values=True)

    # Add UTM parameters (only if not None)
    utm_params: dict[str, str] = {"utm_source": source}
    if medium is not None:
        utm_params["utm_medium"] = medium
    if campaign is not None:
        utm_params["utm_campaign"] = campaign

    # Update params with UTM values (overwrites existing UTM params)
    for key, value in utm_params.items():
        params[key] = [value]

    # Build sorted query string
    # Sort by key, then flatten values (each key has a list of values)
    sorted_params: list[tuple[str, str]] = []
    for key in sorted(params.keys()):
        for val in params[key]:
            sorted_params.append((key, val))

    new_query = urlencode(sorted_params)

    # Reconstruct URL with new query (fragment is preserved automatically)
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)


def is_valid_url(url: str) -> bool:
    """Validate that a string is a valid HTTP/HTTPS URL.

    Args:
        url: The string to validate

    Returns:
        True if the string is a valid HTTP/HTTPS URL, False otherwise
    """
    try:
        parsed = urlparse(url)
        # Must have a scheme and netloc, and scheme must be http or https
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False
