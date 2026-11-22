"""FastAPI logging middleware for structured request logging."""

from __future__ import annotations

import json
import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("internnexus.access")

EXCLUDED_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests with structured JSON output."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        response = await call_next(request)

        duration_ms = round((time.time() - start_time) * 1000, 2)

        if request.url.path in EXCLUDED_PATHS:
            return response

        client_ip = request.headers.get(
            "x-forwarded-for", request.client.host if request.client else "unknown"
        )

        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params) if request.query_params else None,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": client_ip.split(",")[0].strip() if "," in client_ip else client_ip,
            "user_agent": request.headers.get("user-agent"),
        }

        if any(request.url.path.startswith(path) for path in ["/auth", "/login", "/register"]):
            log_entry.pop("query_params", None)

        logger.info(json.dumps(log_entry))

        return response
