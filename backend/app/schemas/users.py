"""User profile, resume, notification, saved-job and MCP-key contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.auth.jwt import ensure_password_strength
from app.schemas.jobs import JobSummaryResponse


class UserProfileResponse(BaseModel):
    id: str
    email: str
    name: str | None
    image: str | None
    created_at: datetime
    bio: str | None
    phone: str | None
    location: str | None
    job_title: str | None
    company: str | None
    industry: str | None
    skills: list[str]
    linkedin_url: str | None
    portfolio_url: str | None
    preferred_locations: list[str]
    has_password: bool

    model_config = ConfigDict(from_attributes=True)


class UpdateUserRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    bio: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, pattern=r"^\+?[\d\s\-().]+$")
    location: str | None = Field(default=None, max_length=100)
    job_title: str | None = Field(default=None, max_length=100)
    company: str | None = Field(default=None, max_length=100)
    industry: str | None = Field(default=None, max_length=50)
    skills: list[str] = Field(default_factory=list, max_length=20)
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    preferred_locations: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("name", "bio", "phone", "location", "job_title", "company", "industry", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("linkedin_url", "portfolio_url", mode="before")
    @classmethod
    def validate_profile_url(cls, value: object, info: ValidationInfo) -> object:
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            return None
        parsed = urlsplit(normalized)
        if (
            parsed.scheme.lower() not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError("URL must be HTTP(S), include a hostname, and not contain credentials")
        if info.field_name == "linkedin_url":
            hostname = parsed.hostname.lower().rstrip(".")
            if hostname != "linkedin.com" and not hostname.endswith(".linkedin.com"):
                raise ValueError("LinkedIn URL must use a linkedin.com hostname")
        return normalized

    @field_validator("skills", "preferred_locations")
    @classmethod
    def validate_list_items(cls, value: list[str], info: ValidationInfo) -> list[str]:
        max_length = 50 if info.field_name == "skills" else 100
        normalized: list[str] = []
        for item in value:
            stripped = item.strip()
            if not stripped:
                raise ValueError("List values cannot be empty")
            if len(stripped) > max_length:
                raise ValueError(f"List values cannot exceed {max_length} characters")
            normalized.append(stripped)
        return normalized


class ChangePasswordRequest(BaseModel):
    current_password: str | None = None
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return ensure_password_strength(v)


class UserResumeResponse(BaseModel):
    id: UUID
    file_name: str
    file_hash: str
    content_hash: str | None = None
    status: str
    has_embedding: bool = False
    embedding_model: str | None = None
    embedding_dim: int | None = None
    last_embedded_at: datetime | None = None
    embedding_error: str | None = None
    uploaded_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseModel):
    id: UUID
    type: str
    payload: dict[str, Any]
    is_read: bool
    created_at: datetime
    read_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SavedJobResponse(BaseModel):
    id: UUID
    job_id: UUID
    created_at: datetime
    job: JobSummaryResponse

    model_config = ConfigDict(from_attributes=True)


class HomeStateResponse(BaseModel):
    """Everything the homepage needs for a signed-in user, in one round trip."""

    unread_count: int
    saved_job_ids: list[UUID]
    applied_job_ids: list[UUID]


class MCPApiKeyResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class CreateMCPApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    expires_in_days: int = Field(default=90, ge=1, le=365)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Key name is required")
        return value


class CreatedMCPApiKeyResponse(MCPApiKeyResponse):
    secret: str
