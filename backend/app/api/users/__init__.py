"""Combined /users router.

One module per concern; this file only assembles them.
"""

from __future__ import annotations

from fastapi import APIRouter

from .home_state import router as home_state_router
from .mcp_keys import router as mcp_keys_router
from .notifications import router as notifications_router
from .profile import router as profile_router
from .resume import router as resume_router
from .saved_jobs import router as saved_jobs_router

router = APIRouter(prefix="/users", tags=["users"])
router.include_router(mcp_keys_router)
router.include_router(profile_router)
router.include_router(resume_router)
router.include_router(notifications_router)
router.include_router(saved_jobs_router)
router.include_router(home_state_router)

__all__ = ["router"]
