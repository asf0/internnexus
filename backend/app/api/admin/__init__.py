"""Combined admin API router."""

from __future__ import annotations

from fastapi import APIRouter

from .clicks import router as clicks_router
from .jobs import router as jobs_router
from .pipeline import router as pipeline_router
from .shared import VALID_PIPELINE_STEPS, _add_admin_audit_log, _commit_or_500
from .users import router as users_router

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(jobs_router)
router.include_router(users_router)
router.include_router(pipeline_router)
router.include_router(clicks_router)

__all__ = ["VALID_PIPELINE_STEPS", "_add_admin_audit_log", "_commit_or_500", "router"]
