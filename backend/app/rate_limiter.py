from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

# Get Redis URL from environment variable, fallback to in-memory for development
redis_url = os.getenv("REDIS_URL")

if redis_url:
    # Use Redis for persistent rate limiting
    limiter = Limiter(key_func=get_remote_address, storage_uri=redis_url)
else:
    # Fallback to in-memory storage for development
    limiter = Limiter(key_func=get_remote_address)

# Rate limit configurations
RATE_LIMITS = {
    "match": "5/minute",  # Expensive operation: PDF parsing + embeddings
    "jobs_list": "60/minute",  # Standard read operation
    "jobs_detail": "60/minute",  # Standard read operation
    "filters": "30/minute",  # Filter endpoints (cached data)
    "health": "1000/minute",  # Health checks - very permissive
}
