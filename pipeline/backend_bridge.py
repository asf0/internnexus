"""Boundary module for backend integrations used by pipeline code."""

from backend.app.config import get_settings
from backend.app.http_client.client import get_http_client
from backend.app.services.embedding_service import EmbeddingError, EmbeddingService, RateLimitError
from backend.app.utils.text import clean_text_for_embedding

__all__ = [
    "get_settings",
    "get_http_client",
    "EmbeddingService",
    "EmbeddingError",
    "RateLimitError",
    "clean_text_for_embedding",
]
