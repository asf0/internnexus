from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.jwt import (
    create_access_token,
    get_password_hash,
    verify_password,
    validate_password_strength,
)
from app.auth.oauth import verify_oauth_token, OAuthVerificationError
from app.auth.crypto import encrypt_token
from app.db import get_db
from app.models import Account, User
from app.rate_limiter import RATE_LIMITS, limiter

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        is_valid, error_message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_message)
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OAuthCallbackRequest(BaseModel):
    provider: str = Field(..., pattern="^(google|github)$")
    provider_account_id: str
    email: EmailStr
    name: str | None = None
    image: str | None = None
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None


class SetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=8)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class ErrorResponse(BaseModel):
    error: str
    message: str
    action: str | None = None


def create_auth_error(error: str, message: str, action: str | None = None, **extra) -> dict:
    detail = {"error": error, "message": message}
    if action:
        detail["action"] = action
    detail.update(extra)
    return detail


@router.post("/register", response_model=AuthResponse)
@limiter.limit(RATE_LIMITS["auth_register"])
async def register(
    request: Request,
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Register a new user with email and password.

    If the email already exists with an OAuth account, returns an error
    suggesting the user set a password instead.
    """
    # Check if user already exists
    stmt = select(User).where(User.email == data.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        # Check if user has OAuth accounts
        oauth_stmt = select(Account).where(
            Account.user_id == existing_user.id, Account.provider.in_(["google", "github"])
        )
        oauth_result = await db.execute(oauth_stmt)
        oauth_accounts = oauth_result.scalars().all()

        if oauth_accounts:
            # User exists with OAuth - suggest setting password
            provider_names = [acc.provider.capitalize() for acc in oauth_accounts]
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=create_auth_error(
                    "EMAIL_REGISTERED_WITH_OAUTH",
                    f"This email is already registered with {', '.join(provider_names)}. "
                    "Please sign in with that provider or set a password for your account.",
                    action="SET_PASSWORD",
                    providers=provider_names,
                ),
            )
        else:
            # User exists with credentials
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=create_auth_error(
                    "EMAIL_ALREADY_REGISTERED",
                    "An account with this email already exists. Please sign in instead.",
                    action="SIGN_IN",
                ),
            )

    # Create new user
    hashed_password = get_password_hash(data.password)
    user = User(
        email=data.email,
        name=data.name,
        hashed_password=hashed_password,
        email_verified=False,
    )
    db.add(user)
    await db.flush()  # Get user.id

    # Create credentials account
    account = Account(
        user_id=user.id,
        provider="credentials",
        provider_account_id=data.email,
    )
    db.add(account)
    await db.commit()

    # Generate JWT token
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    return AuthResponse(
        access_token=access_token,
        user={
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
        },
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit(RATE_LIMITS["auth_login"])
async def login(
    request: Request,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Login with email and password."""
    # Find user by email
    stmt = select(User).where(User.email == data.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=create_auth_error("INVALID_CREDENTIALS", "Invalid email or password."),
        )

    # Check if user has a password set
    if not user.hashed_password:
        # Check if user has OAuth accounts
        oauth_stmt = select(Account).where(
            Account.user_id == user.id, Account.provider.in_(["google", "github"])
        )
        oauth_result = await db.execute(oauth_stmt)
        oauth_accounts = oauth_result.scalars().all()

        if oauth_accounts:
            provider_names = [acc.provider.capitalize() for acc in oauth_accounts]
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=create_auth_error(
                    "OAUTH_ACCOUNT_NO_PASSWORD",
                    f"This account uses {', '.join(provider_names)} authentication. "
                    "Please sign in with that provider or set a password first.",
                    action="USE_OAUTH",
                    providers=provider_names,
                ),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=create_auth_error("INVALID_CREDENTIALS", "Invalid email or password."),
            )

    # Verify password
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=create_auth_error("INVALID_CREDENTIALS", "Invalid email or password."),
        )

    # Generate JWT token
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    return AuthResponse(
        access_token=access_token,
        user={
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
        },
    )


@router.post("/oauth/callback", response_model=AuthResponse)
@limiter.limit(RATE_LIMITS["auth_oauth"])
async def oauth_callback(
    request: Request,
    data: OAuthCallbackRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Handle OAuth callback from providers like Google or GitHub.

    Verifies the OAuth token with the provider before creating/updating the user.
    Creates or updates the user account and returns a backend JWT token.
    """
    try:
        verified_user = await verify_oauth_token(data.provider, data.access_token)
    except OAuthVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=create_auth_error(
                "OAUTH_VERIFICATION_FAILED",
                f"Failed to verify {exc.provider} token: {exc.message}",
            ),
        )

    verified_email = verified_user.email
    verified_provider_account_id = verified_user.provider_account_id

    stmt = select(User).where(User.email == verified_email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    encrypted_access_token = encrypt_token(data.access_token)
    encrypted_refresh_token = encrypt_token(data.refresh_token) if data.refresh_token else None

    if user:
        account_stmt = select(Account).where(
            Account.user_id == user.id,
            Account.provider == data.provider,
            Account.provider_account_id == verified_provider_account_id,
        )
        account_result = await db.execute(account_stmt)
        existing_account = account_result.scalar_one_or_none()

        if existing_account:
            existing_account.access_token = encrypted_access_token
            existing_account.refresh_token = encrypted_refresh_token
            existing_account.expires_at = data.expires_at
        else:
            account = Account(
                user_id=user.id,
                provider=data.provider,
                provider_account_id=verified_provider_account_id,
                access_token=encrypted_access_token,
                refresh_token=encrypted_refresh_token,
                expires_at=data.expires_at,
            )
            db.add(account)

        if verified_user.name and not user.name:
            user.name = verified_user.name
        if verified_user.picture and not user.image:
            user.image = verified_user.picture

    else:
        user = User(
            email=verified_email,
            name=verified_user.name,
            image=verified_user.picture,
            email_verified=True,
        )
        db.add(user)
        await db.flush()

        account = Account(
            user_id=user.id,
            provider=data.provider,
            provider_account_id=verified_provider_account_id,
            access_token=encrypted_access_token,
            refresh_token=encrypted_refresh_token,
            expires_at=data.expires_at,
        )
        db.add(account)

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    return AuthResponse(
        access_token=access_token,
        user={
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
        },
    )


@router.post("/set-password", response_model=AuthResponse)
@limiter.limit(RATE_LIMITS["auth_set_password"])
async def set_password(
    request: Request,
    data: SetPasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Set a password for an OAuth user to enable local authentication."""
    # Hash the new password
    hashed_password = get_password_hash(data.password)
    current_user.hashed_password = hashed_password

    # Check if credentials account already exists
    account_stmt = select(Account).where(
        Account.user_id == current_user.id, Account.provider == "credentials"
    )
    account_result = await db.execute(account_stmt)
    credentials_account = account_result.scalar_one_or_none()

    if not credentials_account:
        # Create credentials account
        account = Account(
            user_id=current_user.id,
            provider="credentials",
            provider_account_id=current_user.email,
        )
        db.add(account)

    await db.commit()

    # Generate new JWT token
    access_token = create_access_token(
        data={"sub": str(current_user.id), "email": current_user.email}
    )

    return AuthResponse(
        access_token=access_token,
        user={
            "id": str(current_user.id),
            "email": current_user.email,
            "name": current_user.name,
        },
    )
