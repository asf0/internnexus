from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin import router
from app.api.admin.pipeline import trigger_pipeline_run
from app.api.admin.shared import VALID_PIPELINE_STEPS
from app.schemas.admin import PipelineCommandTriggerRequest
from app.models import Admin


def _route_methods_by_path() -> dict[str, set[str]]:
    app = FastAPI()
    app.include_router(router)
    return {
        path: {method.upper() for method in operations}
        for path, operations in app.openapi()["paths"].items()
    }


def test_admin_combined_router_preserves_representative_paths():
    routes = _route_methods_by_path()

    assert "GET" in routes["/admin/jobs"]
    assert "POST" in routes["/admin/jobs"]
    assert "GET" in routes["/admin/jobs/stats"]
    assert "POST" in routes["/admin/jobs/bulk"]
    assert "GET" in routes["/admin/users"]
    assert "POST" in routes["/admin/users"]
    assert "GET" in routes["/admin/users/export"]
    assert "GET" in routes["/admin/me"]
    assert "GET" in routes["/admin/pipeline-runs"]
    assert "POST" in routes["/admin/pipeline-runs/trigger"]
    assert "GET" in routes["/admin/clicks"]
    assert "GET" in routes["/admin/clicks/stats"]


def test_admin_router_has_expected_domain_route_count():
    routes = _route_methods_by_path()
    assert len(routes) >= 25


def test_users_export_route_precedes_dynamic_user_id_route():
    """`/admin/users/export` must be declared before `/admin/users/{user_id}`.

    FastAPI matches in declaration order, so otherwise the literal path is
    shadowed by the UUID route and returns 422.
    """
    from app.api.admin.users import router as users_router

    paths = [route.path for route in users_router.routes]
    assert paths.index("/users/export") < paths.index("/users/{user_id}")


@pytest.mark.asyncio
async def test_trigger_pipeline_rejects_removed_sync_inactive_before_queueing() -> None:
    class _RejectingDb:
        added = False

        def add(self, _value) -> None:
            self.added = True

    db = _RejectingDb()
    endpoint = inspect.unwrap(trigger_pipeline_run)

    assert "sync_inactive" not in VALID_PIPELINE_STEPS
    with pytest.raises(HTTPException) as exc_info:
        await endpoint(
            request=cast(Request, object()),
            data=PipelineCommandTriggerRequest(step="sync_inactive"),
            admin=cast(Admin, SimpleNamespace(user_id=uuid4())),
            db=cast(AsyncSession, db),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == f"Invalid step. Must be one of: {sorted(VALID_PIPELINE_STEPS)}"
    assert db.added is False
