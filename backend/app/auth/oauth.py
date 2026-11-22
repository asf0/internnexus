"""OAuth token verification for Google and GitHub providers."""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass

import httpx

from app.infra.config import get_settings

logger = logging.getLogger(__name__)
_PROVIDER_DISABLED = "Provider is disabled"


@dataclass
class VerifiedOAuthUser:
    """Verified OAuth user information from provider."""

    provider: str
    provider_account_id: str
    email: str
    name: str | None = None
    picture: str | None = None


class OAuthVerificationError(Exception):
    """Raised when OAuth token verification fails."""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        self.message = message
        super().__init__(f"{provider} verification failed: {message}")


async def verify_google_token(access_token: str) -> VerifiedOAuthUser:
    """Verify Google OAuth access token.

    Calls Google's tokeninfo endpoint to validate the token and extract user info.

    Args:
        access_token: Google OAuth access token

    Returns:
        VerifiedOAuthUser with verified email and profile info

    Raises:
        OAuthVerificationError: If token is invalid or verification fails
    """
    url = "https://www.googleapis.com/oauth2/v3/tokeninfo"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params={"access_token": access_token})

            if response.status_code == 400:
                raise OAuthVerificationError("google", "Invalid or expired token")

            response.raise_for_status()
            data = response.json()

    except httpx.TimeoutException:
        raise OAuthVerificationError("google", "Verification request timed out")
    except httpx.RequestError as exc:
        raise OAuthVerificationError("google", f"Network error: {exc}")
    except httpx.HTTPStatusError as exc:
        raise OAuthVerificationError("google", f"HTTP error {exc.response.status_code}")

    email = data.get("email")
    if not email:
        raise OAuthVerificationError("google", "Token does not contain email")

    if data.get("email_verified") not in (True, "true"):
        raise OAuthVerificationError("google", "Email is not verified by Google")

    sub = data.get("sub")
    if not sub:
        raise OAuthVerificationError("google", "Token does not contain user ID")

    settings = get_settings()
    if not (settings.google_client_id and settings.google_client_secret):
        raise OAuthVerificationError("google", _PROVIDER_DISABLED)
    aud = data.get("aud")
    if aud != settings.google_client_id:
        raise OAuthVerificationError("google", "Token was not issued for this application")

    return VerifiedOAuthUser(
        provider="google",
        provider_account_id=sub,
        email=email,
        name=data.get("name"),
        picture=data.get("picture"),
    )


async def verify_github_token(access_token: str) -> VerifiedOAuthUser:
    """Verify GitHub OAuth access token.

    Calls GitHub's /user API to validate the token and extract user info.

    Args:
        access_token: GitHub OAuth access token

    Returns:
        VerifiedOAuthUser with verified email and profile info

    Raises:
        OAuthVerificationError: If token is invalid or verification fails
    """
    url = "https://api.github.com/user"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "InternNexus-OAuth",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 401:
                raise OAuthVerificationError("github", "Invalid or expired token")
            if response.status_code == 403:
                raise OAuthVerificationError("github", "Token lacks required scope")

            response.raise_for_status()
            data = response.json()

    except httpx.TimeoutException:
        raise OAuthVerificationError("github", "Verification request timed out")
    except httpx.RequestError as exc:
        raise OAuthVerificationError("github", f"Network error: {exc}")
    except httpx.HTTPStatusError as exc:
        raise OAuthVerificationError("github", f"HTTP error {exc.response.status_code}")

    user_id = data.get("id")
    if not user_id:
        raise OAuthVerificationError("github", "Response does not contain user ID")

    settings = get_settings()
    if not (settings.gh_client_id and settings.gh_client_secret):
        raise OAuthVerificationError("github", _PROVIDER_DISABLED)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            auth = base64.b64encode(f"{settings.gh_client_id}:{settings.gh_client_secret}".encode()).decode()
            check_response = await client.post(
                f"https://api.github.com/applications/{settings.gh_client_id}/token",
                headers={
                    "Authorization": f"Basic {auth}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "InternNexus-OAuth",
                },
                json={"access_token": access_token},
            )
            if check_response.status_code != 200:
                raise OAuthVerificationError("github", "Token was not issued for this application")
            email_response = await client.get("https://api.github.com/user/emails", headers=headers)
            email_response.raise_for_status()
            emails = email_response.json()
    except OAuthVerificationError:
        raise
    except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError):
        raise OAuthVerificationError("github", "Token ownership or email verification failed")

    email = next(
        (
            item.get("email")
            for item in emails
            if item.get("primary") is True and item.get("verified") is True and item.get("email")
        ),
        None,
    )
    if not email:
        raise OAuthVerificationError("github", "Account has no verified primary email")

    return VerifiedOAuthUser(
        provider="github",
        provider_account_id=str(user_id),
        email=email,
        name=data.get("name"),
        picture=data.get("avatar_url"),
    )


async def verify_oauth_token(provider: str, access_token: str) -> VerifiedOAuthUser:
    """Verify OAuth token with the appropriate provider.

    Args:
        provider: OAuth provider name ("google" or "github")
        access_token: OAuth access token to verify

    Returns:
        VerifiedOAuthUser with verified user information

    Raises:
        OAuthVerificationError: If provider is unsupported or verification fails
    """
    settings = get_settings()
    if provider == "google":
        if not (settings.google_client_id and settings.google_client_secret):
            raise OAuthVerificationError(provider, _PROVIDER_DISABLED)
        return await verify_google_token(access_token)
    elif provider == "github":
        if not (settings.gh_client_id and settings.gh_client_secret):
            raise OAuthVerificationError(provider, _PROVIDER_DISABLED)
        return await verify_github_token(access_token)
    raise OAuthVerificationError(provider, f"Unsupported OAuth provider: {provider}")
