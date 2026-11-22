"""Combined admin API router."""

from __future__ import annotations

from fastapi import APIRouter

from .clicks import router as clicks_router
from .jobs import router as jobs_router
from .mcp_usage import router as mcp_usage_router
from .pipeline import router as pipeline_router
from .users import router as users_router

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(jobs_router)
router.include_router(users_router)
router.include_router(pipeline_router)
router.include_router(clicks_router)
router.include_router(mcp_usage_router)

__all__ = ["router"]
