from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.auth import router as auth_router
from app.api.jobs import router as jobs_router
from app.api.matching import router as matching_router
from app.api.users import router as users_router
from app.middleware.logging import RequestLoggingMiddleware
from app.rate_limiter import limiter, RATE_LIMITS

logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[logging.StreamHandler()])

app = FastAPI(title="InternNexus API", version="1.0.0")

# Add rate limiter to app state
app.state.limiter = limiter


# Add rate limit exceeded exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please try again later.",
            "retry_after": exc.retry_after if hasattr(exc, "retry_after") else None,
        },
        headers={"Retry-After": str(exc.retry_after) if hasattr(exc, "retry_after") else "60"},
    )


origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(jobs_router, tags=["jobs"])
app.include_router(matching_router, tags=["matching"])


@app.get("/health")
@limiter.limit(RATE_LIMITS["health"])
def health_check(request: Request) -> dict[str, str]:
    return {"status": "ok"}
