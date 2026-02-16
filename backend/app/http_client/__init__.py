"""HTTP client module with connection pooling."""

from app.http_client.client import get_http_client, close_http_client

__all__ = ["get_http_client", "close_http_client"]
