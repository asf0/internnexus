from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.jobs import router as jobs_router
from app.api.matching import router as matching_router
from app.api.users import router as users_router
from app.cache.redis_pool import close_redis_pool
from app.db import async_engine
from app.http_client.client import close_http_client
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.query_timing import setup_query_timing
from app.middleware.security import SecurityHeadersMiddleware
from app.rate_limiter import RATE_LIMITS, limiter
from app.services.errors import APIError

logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[logging.StreamHandler()])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    setup_query_timing(async_engine)
    yield
    await close_redis_pool()
    await close_http_client()


app = FastAPI(title="InternNexus API", version="1.0.0", lifespan=lifespan)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please try again later.",
            "retry_after": getattr(exc, "retry_after", None),
        },
        headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
    )


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.to_dict()})


origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(jobs_router, tags=["jobs"])
app.include_router(matching_router, tags=["matching"])
app.include_router(admin_router, tags=["admin"])


@app.get("/health")
@limiter.limit(RATE_LIMITS["health"])
def health_check(request: Request) -> dict[str, str]:
    return {"status": "ok"}
