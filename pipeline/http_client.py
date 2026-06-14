"""Compatibility re-export — implementation moved to internnexus-core."""

from internnexus_core.http_client import close_http_client, get_http_client

__all__ = ["get_http_client", "close_http_client"]
