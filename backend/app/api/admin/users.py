"""Admin user management routes."""

from __future__ import annotations

import csv
import io
import logging
import math
import typing
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.admin_schemas import (
    AdminListResponse,
    AdminUserResponse,
    JobClickResponse,
    UserCreateRequest,
    UserNotesUpdateRequest,
)
from app.api.mappers import user_to_admin_response
from app.auth.dependencies import AdminDep, SuperAdminDep
from app.auth.jwt import get_password_hash
from app.db import get_db
from app.models import Admin, AdminRole, Job, JobClick, User
from app.rate_limiter import RATE_LIMITS, limiter

from .shared import _add_admin_audit_log, _commit_or_500

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================================================
# User Management Endpoints
# ============================================================================


class GrantAdminRequest(BaseModel):
    """Schema for granting admin access request."""

    notes: str | None = None
    role: str = "admin"


@router.get("/users", response_model=AdminListResponse[AdminUserResponse])
@limiter.limit(RATE_LIMITS["admin_read"])
async def list_users(
    request: Request,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search in email and name"),
    is_admin: bool | None = Query(None, description="Filter by admin status"),
) -> AdminListResponse[AdminUserResponse]:
    """List users with pagination, search, and admin filter.

    Args:
        request: FastAPI request object for rate limiting
        admin: Authenticated admin user
        db: Database session
        page: Page number (1-indexed)
        page_size: Number of items per page
        search: Optional search term for email and name (case-insensitive)
        is_admin: Optional filter by admin status

    Returns:
        Paginated list of users with admin role and provider info
    """
    # Build base query with relationships
    query = (
        select(User)
        .options(
            selectinload(User.admin),
            selectinload(User.accounts),
        )
        .order_by(User.created_at.desc())
    )

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                User.email.ilike(search_pattern),
                User.name.ilike(search_pattern),
            )
        )

    # Apply admin filter
    if is_admin is not None:
        admin_exists = select(Admin).where(Admin.user_id == User.id).exists()
        if is_admin:
            query = query.where(admin_exists)
        else:
            query = query.where(~admin_exists)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()

    # Build response items
    items = [user_to_admin_response(user) for user in users]

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return AdminListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/users/{user_id}", response_model=AdminUserResponse)
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_user(
    request: Request,
    user_id: UUID,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
) -> AdminUserResponse:
    """Get a single user by ID.

    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to retrieve
        admin: Authenticated admin user
        db: Database session

    Returns:
        User details with admin role and provider info

    Raises:
        HTTPException: 404 if user not found
    """
    query = (
        select(User)
        .options(
            selectinload(User.admin),
            selectinload(User.accounts),
        )
        .where(User.id == user_id)
    )

    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user_to_admin_response(user)


@router.post("/users/{user_id}/grant-admin")
@limiter.limit(RATE_LIMITS["admin_destructive"])
async def grant_admin(
    request: Request,
    user_id: UUID,
    data: GrantAdminRequest,
    super_admin: SuperAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Grant admin access to a user. Only super admins can grant admin access.

    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to grant admin access
        data: Request body with optional notes and role
        super_admin: Authenticated super admin user
        db: Database session

    Returns:
        Success message with granted role

    Raises:
        HTTPException: 404 if user not found, 400 if invalid role
    """
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate role
    try:
        role = AdminRole(data.role)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {[r.value for r in AdminRole]}",
        )

    # Check if admin record already exists
    admin_result = await db.execute(select(Admin).where(Admin.user_id == user_id))
    existing_admin = admin_result.scalar_one_or_none()

    if existing_admin:
        # Update existing admin record
        existing_admin.role = role
        existing_admin.granted_by = super_admin.user_id
        existing_admin.granted_at = datetime.now(timezone.utc)
        if data.notes is not None:
            existing_admin.notes = data.notes
    else:
        # Create new admin record
        new_admin = Admin(
            user_id=user_id,
            role=role,
            granted_by=super_admin.user_id,
            notes=data.notes,
        )
        db.add(new_admin)

    await _add_admin_audit_log(
        db,
        actor_user_id=super_admin.user_id,
        action="admin.grant",
        target_type="user",
        target_id=user_id,
        metadata={"role": role.value},
    )
    await _commit_or_500(db, "grant admin")

    return {"message": "Admin access granted", "role": role.value}


@router.delete("/users/{user_id}/revoke-admin")
@limiter.limit(RATE_LIMITS["admin_destructive"])
async def revoke_admin(
    request: Request,
    user_id: UUID,
    super_admin: SuperAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Revoke admin access from a user. Only super admins can revoke admin access.

    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to revoke admin access
        super_admin: Authenticated super admin user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if user is not an admin, 400 if trying to revoke own access
    """
    # Check if admin record exists
    admin_result = await db.execute(select(Admin).where(Admin.user_id == user_id))
    admin = admin_result.scalar_one_or_none()

    if not admin:
        raise HTTPException(status_code=404, detail="User is not an admin")

    # Prevent self-revocation
    if admin.user_id == super_admin.user_id:
        raise HTTPException(status_code=400, detail="Cannot revoke your own admin access")

    await _add_admin_audit_log(
        db,
        actor_user_id=super_admin.user_id,
        action="admin.revoke",
        target_type="user",
        target_id=user_id,
    )
    await db.delete(admin)
    await _commit_or_500(db, "revoke admin")

    return {"message": "Admin access revoked"}


@router.post("/users/{user_id}/deactivate")
@limiter.limit(RATE_LIMITS["admin_destructive"])
async def deactivate_user(
    request: Request,
    user_id: UUID,
    super_admin: SuperAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Deactivate a user account. Only super admins can deactivate users.

    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to deactivate
        super_admin: Authenticated super admin user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if user not found, 400 if trying to deactivate self
    """
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-deactivation
    if user.id == super_admin.user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    # Deactivate user
    user.is_deleted = True
    user.deleted_at = datetime.now(timezone.utc)

    await _add_admin_audit_log(
        db,
        actor_user_id=super_admin.user_id,
        action="user.deactivate",
        target_type="user",
        target_id=user_id,
        metadata={"email": user.email},
    )
    await _commit_or_500(db, "deactivate user")

    return {"message": "User deactivated"}


@router.post("/users/{user_id}/reactivate")
@limiter.limit(RATE_LIMITS["admin_write"])
async def reactivate_user(
    request: Request,
    user_id: UUID,
    super_admin: SuperAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Reactivate a user account. Only super admins can reactivate users.

    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to reactivate
        super_admin: Authenticated super admin user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if user not found
    """
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Reactivate user
    user.is_deleted = False
    user.deleted_at = None

    await _add_admin_audit_log(
        db,
        actor_user_id=super_admin.user_id,
        action="user.reactivate",
        target_type="user",
        target_id=user_id,
        metadata={"email": user.email},
    )
    await _commit_or_500(db, "reactivate user")

    return {"message": "User reactivated"}


@router.post("/users", response_model=AdminUserResponse, status_code=201)
@limiter.limit(RATE_LIMITS["admin_destructive"])
async def create_user(
    request: Request,
    data: UserCreateRequest,
    super_admin: SuperAdminDep,
    db: AsyncSession = Depends(get_db),
) -> AdminUserResponse:
    """Create a new user with email and password. Only super admins can create users.

    Args:
        request: FastAPI request object for rate limiting
        data: User creation request with email, password, and optional name
        super_admin: Authenticated super admin user
        db: Database session

    Returns:
        Created user details

    Raises:
        HTTPException: 400 if email already exists
    """
    # Check if email already exists
    existing_result = await db.execute(select(User).where(User.email == data.email))
    existing_user = existing_result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password and create user
    hashed_password = get_password_hash(data.password)
    new_user = User(
        email=data.email,
        hashed_password=hashed_password,
        name=data.name,
        email_verified=False,
    )
    db.add(new_user)
    await db.flush()
    await _add_admin_audit_log(
        db,
        actor_user_id=super_admin.user_id,
        action="user.create",
        target_type="user",
        target_id=new_user.id,
        metadata={"email": new_user.email},
    )
    await _commit_or_500(db, "create user")
    await db.refresh(new_user)

    return user_to_admin_response(new_user)


@router.delete("/users/{user_id}/hard")
@limiter.limit(RATE_LIMITS["admin_destructive"])
async def hard_delete_user(
    request: Request,
    user_id: UUID,
    super_admin: SuperAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Permanently delete a user from the database. Only super admins can hard delete users.

    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to delete
        super_admin: Authenticated super admin user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if user not found, 400 if trying to delete self
    """
    # Prevent self-deletion
    if user_id == super_admin.user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Hard delete user
    await _add_admin_audit_log(
        db,
        actor_user_id=super_admin.user_id,
        action="user.hard_delete",
        target_type="user",
        target_id=user_id,
        metadata={"email": user.email},
    )
    await db.delete(user)
    await _commit_or_500(db, "hard delete user")

    return {"message": "User permanently deleted"}


@router.post("/users/{user_id}/reset-password")
@limiter.limit(RATE_LIMITS["admin_destructive"])
async def reset_user_password(
    request: Request,
    user_id: UUID,
    super_admin: SuperAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Initiate password reset for a user. Only super admins can reset passwords.

    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to reset password for
        super_admin: Authenticated super admin user
        db: Database session

    Raises:
        HTTPException: 404 if user not found, 501 if reset email delivery is not configured
    """
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(f"Password reset requested for user {user_id} by super admin {super_admin.user_id}")
    await _add_admin_audit_log(
        db,
        actor_user_id=super_admin.user_id,
        action="user.password_reset_requested",
        target_type="user",
        target_id=user_id,
        metadata={"email": user.email},
    )
    await _commit_or_500(db, "request password reset")

    raise HTTPException(
        status_code=501,
        detail="Password reset email delivery is not configured.",
    )


@router.get("/users/{user_id}/clicks", response_model=AdminListResponse[JobClickResponse])
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_user_clicks(
    request: Request,
    user_id: UUID,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> AdminListResponse[JobClickResponse]:
    """Get paginated list of job clicks for a specific user.

    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to get clicks for
        admin: Authenticated admin user
        db: Database session
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Paginated list of job clicks with job title and company

    Raises:
        HTTPException: 404 if user not found
    """
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Build base query with join to get user info
    base_query = (
        select(JobClick, Job.title, Job.company, User.email, User.name)
        .join(Job, JobClick.job_id == Job.id)
        .outerjoin(User, JobClick.user_id == User.id)
        .where(JobClick.user_id == user_id)
        .order_by(JobClick.clicked_at.desc())
    )

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    paginated_query = base_query.offset(offset).limit(page_size)

    result = await db.execute(paginated_query)
    rows = result.all()

    # Build response items
    items = [
        JobClickResponse(
            id=row.JobClick.id,
            job_id=row.JobClick.job_id,
            job_title=row.title,
            company=row.company,
            user_id=row.JobClick.user_id,
            user_email=row.email,
            user_name=row.name,
            clicked_at=row.JobClick.clicked_at,
            utm_source=row.JobClick.utm_source,
            utm_medium=row.JobClick.utm_medium,
            utm_campaign=row.JobClick.utm_campaign,
        )
        for row in rows
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return AdminListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch("/users/{user_id}/notes")
@limiter.limit(RATE_LIMITS["admin_write"])
async def update_user_notes(
    request: Request,
    user_id: UUID,
    data: UserNotesUpdateRequest,
    super_admin: SuperAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Update notes for a user. Only super admins can update user notes.

    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to update notes for
        data: Request body with notes (can be null to clear)
        super_admin: Authenticated super admin user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if user not found
    """
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update notes directly in SQL since notes is not ORM-mapped in compatibility mode
    await db.execute(
        text("UPDATE users SET notes = :notes WHERE id = :user_id"),
        {"notes": data.notes, "user_id": user_id},
    )
    await _add_admin_audit_log(
        db,
        actor_user_id=super_admin.user_id,
        action="user.notes_update",
        target_type="user",
        target_id=user_id,
    )
    await _commit_or_500(db, "update user notes")

    return {"message": "User notes updated"}


_FORMULA_PREFIX_CHARS = ("=", "+", "-", "@", "\t", "\r")


def _sanitize_csv_cell(value: str | None) -> str:
    """Neutralize spreadsheet formula injection in CSV cells.

    Prefixes values that could be interpreted as formulas by spreadsheet
    applications (Excel, LibreOffice Calc, Google Sheets) with a single quote.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        return str(value)
    stripped = value.lstrip()
    if stripped and stripped[0] in _FORMULA_PREFIX_CHARS:
        return "'" + value
    return value


@router.get("/users/export")
@limiter.limit(RATE_LIMITS["admin_read"])
async def export_users_csv(
    request: Request,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export all users as a CSV file.

    Args:
        request: FastAPI request object for rate limiting
        admin: Authenticated admin user
        db: Database session

    Returns:
        StreamingResponse with CSV content for download
    """
    # Query all users with admin and account relationships
    query = (
        select(User)
        .options(
            selectinload(User.admin),
            selectinload(User.accounts),
        )
        .order_by(User.created_at.desc())
    )

    result = await db.execute(query)
    users = result.scalars().all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id",
            "email",
            "name",
            "is_active",
            "has_password",
            "admin_role",
            "provider",
            "created_at",
            "notes",
        ],
    )
    writer.writeheader()

    for user in users:
        admin_role = None
        if user.admin:
            admin_role = user.admin.role.value

        provider = None
        if user.accounts:
            provider = user.accounts[0].provider

        writer.writerow(
            {
                "id": str(user.id),
                "email": _sanitize_csv_cell(user.email),
                "name": _sanitize_csv_cell(user.name),
                "is_active": str(not user.is_deleted),
                "has_password": str(user.hashed_password is not None),
                "admin_role": _sanitize_csv_cell(admin_role),
                "provider": _sanitize_csv_cell(provider),
                "created_at": _sanitize_csv_cell(user.created_at.isoformat() if user.created_at else ""),
                "notes": _sanitize_csv_cell(user.notes),
            }
        )

    # Reset buffer position
    output.seek(0)

    # Create streaming response
    def iter_csv() -> typing.Iterator[str]:
        yield output.getvalue()

    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=users_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        },
    )


@router.get("/me")
@limiter.limit(RATE_LIMITS["admin_read"])
async def get_current_admin_info(
    request: Request,
    admin: AdminDep,
) -> dict[str, str]:
    """Return current admin identity and role for the admin UI."""
    return {"id": str(admin.user_id), "role": admin.role.value}
