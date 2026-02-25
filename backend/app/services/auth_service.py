"""Authentication service for business logic."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.crypto import encrypt_token
from app.auth.jwt import create_access_token, get_password_hash, verify_password
from app.db import get_db
from app.models import User
from app.repositories.account import AccountRepository, PasswordHistoryRepository
from app.repositories.user import UserRepository
from app.services.errors import AuthErrorMessages, ConflictError, create_auth_error


class AuthService:
    """Service for authentication business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.account_repo = AccountRepository(session)
        self.password_repo = PasswordHistoryRepository(session)

    async def register_user(
        self,
        email: str,
        password: str,
        name: str | None = None,
    ) -> tuple[User, str]:
        """Register a new user with email and password.

        Returns:
            Tuple of (User, access_token)

        Raises:
            ConflictError: If email already registered
        """
        existing_user = await self.user_repo.get_by_email(email)

        if existing_user:
            oauth_providers = await self.account_repo.get_oauth_providers(existing_user.id)
            if oauth_providers:
                raise ConflictError(
                    message=AuthErrorMessages.EMAIL_REGISTERED_WITH_OAUTH.format(
                        providers=", ".join(oauth_providers)
                    ),
                    action="SET_PASSWORD",
                    providers=oauth_providers,
                )
            else:
                raise ConflictError(
                    message=AuthErrorMessages.EMAIL_ALREADY_REGISTERED,
                    action="SIGN_IN",
                )

        hashed_password = get_password_hash(password)
        user = await self.user_repo.create_user(
            email=email,
            hashed_password=hashed_password,
            name=name,
            email_verified=False,
        )

        await self.account_repo.create_credentials_account(user.id, email)
        await self.session.commit()

        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email},
            password_changed_at=user.password_changed_at,
        )

        return user, access_token

    async def login_user(self, email: str, password: str) -> tuple[User, str]:
        """Login a user with email and password.

        Returns:
            Tuple of (User, access_token)

        Raises:
            AuthenticationError: If credentials invalid
        """
        from fastapi import HTTPException, status

        user = await self.user_repo.get_by_email(email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=create_auth_error(
                    "INVALID_CREDENTIALS", AuthErrorMessages.INVALID_CREDENTIALS
                ),
            )

        if not user.hashed_password:
            oauth_providers = await self.account_repo.get_oauth_providers(user.id)
            if oauth_providers:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=create_auth_error(
                        "OAUTH_ACCOUNT_NO_PASSWORD",
                        AuthErrorMessages.OAUTH_ACCOUNT_NO_PASSWORD.format(
                            providers=", ".join(oauth_providers)
                        ),
                        action="USE_OAUTH",
                        providers=oauth_providers,
                    ),
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=create_auth_error(
                        "INVALID_CREDENTIALS", AuthErrorMessages.INVALID_CREDENTIALS
                    ),
                )

        if not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=create_auth_error(
                    "INVALID_CREDENTIALS", AuthErrorMessages.INVALID_CREDENTIALS
                ),
            )

        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email},
            password_changed_at=user.password_changed_at,
        )

        return user, access_token

    async def handle_oauth_callback(
        self,
        provider: str,
        provider_account_id: str,
        email: str,
        name: str | None = None,
        picture: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[User, str]:
        """Handle OAuth callback and create/update user.

        Returns:
            Tuple of (User, access_token)
        """
        user = await self.user_repo.get_by_email(email)

        encrypted_access_token = encrypt_token(access_token) if access_token else None
        encrypted_refresh_token = encrypt_token(refresh_token) if refresh_token else None

        if user:
            existing_account = await self.account_repo.get_by_provider(
                user.id, provider, provider_account_id
            )

            if existing_account:
                existing_account.access_token = encrypted_access_token
                existing_account.refresh_token = encrypted_refresh_token
                existing_account.expires_at = expires_at
            else:
                await self.account_repo.create_oauth_account(
                    user_id=user.id,
                    provider=provider,
                    provider_account_id=provider_account_id,
                    access_token=encrypted_access_token,
                    refresh_token=encrypted_refresh_token,
                    expires_at=expires_at,
                )

            if name and not user.name:
                user.name = name
            if picture and not user.image:
                user.image = picture

        else:
            user = await self.user_repo.create_user(
                email=email,
                name=name,
                image=picture,
                email_verified=True,
            )

            await self.account_repo.create_oauth_account(
                user_id=user.id,
                provider=provider,
                provider_account_id=provider_account_id,
                access_token=encrypted_access_token,
                refresh_token=encrypted_refresh_token,
                expires_at=expires_at,
            )

        await self.session.commit()
        await self.user_repo.refresh(user)

        jwt_token = create_access_token(
            data={"sub": str(user.id), "email": user.email},
            password_changed_at=user.password_changed_at,
        )

        return user, jwt_token

    async def set_password(self, user: User, password: str) -> tuple[User, str]:
        """Set a password for an OAuth user.

        Returns:
            Tuple of (User, access_token)
        """
        hashed_password = get_password_hash(password)
        user.hashed_password = hashed_password
        user.password_changed_at = datetime.now(timezone.utc)

        credentials_account = await self.account_repo.get_credentials_account(user.id)
        if not credentials_account:
            await self.account_repo.create_credentials_account(user.id, user.email)

        await self.session.commit()
        await self.user_repo.refresh(user)

        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email},
            password_changed_at=user.password_changed_at,
        )

        return user, access_token

    async def change_password(
        self,
        user: User,
        current_password: str | None,
        new_password: str,
    ) -> None:
        """Change a user's password.

        Raises:
            HTTPException: If current password is incorrect or new password is reused
        """
        from fastapi import HTTPException, status

        if user.hashed_password:
            if not current_password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "Current password is required"},
                )
            if not verify_password(current_password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"message": "Current password is incorrect"},
                )

        if user.hashed_password and verify_password(new_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "New password cannot be the same as the current password"},
            )

        password_history = await self.password_repo.get_recent_passwords(user.id, limit=3)
        for history_entry in password_history:
            if verify_password(new_password, history_entry.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Cannot reuse a previous password. Please choose a different password."
                    },
                )

        if user.hashed_password:
            await self.password_repo.add_password_history(user.id, user.hashed_password)
            await self.password_repo.delete_old_password_history(user.id, keep=3)

        user.hashed_password = get_password_hash(new_password)
        user.password_changed_at = datetime.now(timezone.utc)

        credentials_account = await self.account_repo.get_credentials_account(user.id)
        if not credentials_account:
            await self.account_repo.create_credentials_account(user.id, user.email)

        await self.session.commit()


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Dependency to get AuthService instance."""
    return AuthService(db)
