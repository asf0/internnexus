from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
import os


def get_real_client_ip(request):
    """Get client IP behind Cloudflare."""
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


redis_url = os.getenv("REDIS_URL")

RATE_LIMITS = {
    "match": "5/minute",
    "jobs_list": "60/minute",
    "jobs_detail": "60/minute",
    "filters": "30/minute",
    "health": "1000/minute",
    "auth_register": "5/minute",
    "auth_login": "10/minute",
    "auth_oauth": "20/minute",
    "auth_set_password": "5/minute",
    "user_me": "60/minute",
    "user_update": "20/minute",
    "user_delete": "5/hour",
}
if redis_url:
    limiter = Limiter(key_func=get_real_client_ip, storage_uri=redis_url)
else:
    limiter = Limiter(key_func=get_real_client_ip)
