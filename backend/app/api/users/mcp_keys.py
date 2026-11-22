"""MCP API key management for the signed-in user."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users.dependencies import current_user_dependency
from app.infra.db import get_db
from app.models import User
from app.infra.rate_limiter import RATE_LIMITS, limiter
from app.schemas.users import CreateMCPApiKeyRequest, CreatedMCPApiKeyResponse, MCPApiKeyResponse
from app.services.mcp.api_key import MCPApiKeyService

router = APIRouter()


@router.get("/me/mcp-keys", response_model=list[MCPApiKeyResponse])
@limiter.limit(RATE_LIMITS["user_me"])
async def list_mcp_api_keys(
    request: Request,
    current_user: Annotated[User, Depends(current_user_dependency)],
    db: AsyncSession = Depends(get_db),
) -> list[MCPApiKeyResponse]:
    records = await MCPApiKeyService(db).list_for_user(current_user.id)
    return [MCPApiKeyResponse.model_validate(record) for record in records]


@router.post("/me/mcp-keys", response_model=CreatedMCPApiKeyResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RATE_LIMITS["user_update"])
async def create_mcp_api_key(
    request: Request,
    data: CreateMCPApiKeyRequest,
    current_user: Annotated[User, Depends(current_user_dependency)],
    db: AsyncSession = Depends(get_db),
) -> CreatedMCPApiKeyResponse:
    created = await MCPApiKeyService(db).create(
        current_user.id, data.name, data.expires_in_days
    )
    return CreatedMCPApiKeyResponse(
        **MCPApiKeyResponse.model_validate(created.record).model_dump(), secret=created.secret
    )


@router.delete("/me/mcp-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(RATE_LIMITS["user_update"])
async def revoke_mcp_api_key(
    request: Request,
    key_id: UUID,
    current_user: Annotated[User, Depends(current_user_dependency)],
    db: AsyncSession = Depends(get_db),
) -> None:
    if not await MCPApiKeyService(db).revoke(current_user.id, key_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP API key not found")
