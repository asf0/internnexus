"""Integration tests for admin user export and notes persistence.

These require a real PostgreSQL test database and are gated as integration
tests; they cannot run without the test database.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Admin, AdminRole, User


async def _register_admin(client, db_session: AsyncSession) -> str:
    email = f"admin_{uuid4().hex[:8]}@example.com"
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": "SecurePass123!", "name": "Admin User"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    user_id = UUID(response.json()["user"]["id"])

    db_session.add(Admin(id=uuid4(), user_id=user_id, role=AdminRole.super_admin))
    await db_session.commit()
    return token


@pytest.mark.integration
class TestAdminUsersExportAndNotes:
    @pytest.mark.asyncio
    async def test_export_route_is_not_shadowed_by_user_id_route(self, client, db_session):
        token = await _register_admin(client, db_session)

        response = await client.get(
            "/admin/users/export", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=users_export_" in response.headers["content-disposition"]
        assert "id,email,name,is_active,has_password,admin_role,provider,created_at,notes" in response.text

    @pytest.mark.asyncio
    async def test_notes_persist_reload_and_export(self, client, db_session):
        token = await _register_admin(client, db_session)

        register = await client.post(
            "/auth/register",
            json={
                "email": f"noted_{uuid4().hex[:8]}@example.com",
                "password": "SecurePass123!",
                "name": "Noted User",
            },
        )
        target_id = register.json()["user"]["id"]

        headers = {"Authorization": f"Bearer {token}"}
        save = await client.patch(
            f"/admin/users/{target_id}/notes", json={"notes": "first note"}, headers=headers
        )
        assert save.status_code == 200

        detail = await client.get(f"/admin/users/{target_id}", headers=headers)
        assert detail.json()["notes"] == "first note"

        export = await client.get("/admin/users/export", headers=headers)
        assert "first note" in export.text

        clear = await client.patch(
            f"/admin/users/{target_id}/notes", json={"notes": None}, headers=headers
        )
        assert clear.status_code == 200
        reloaded = await client.get(f"/admin/users/{target_id}", headers=headers)
        assert reloaded.json()["notes"] is None

        # Confirm the value is on the persisted column, not just the ORM identity map.
        db_session.expire_all()
        row = await db_session.execute(select(User.notes).where(User.id == target_id))
        assert row.scalar_one() is None
