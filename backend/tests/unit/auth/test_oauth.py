from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.auth.oauth import OAuthVerificationError, verify_github_token, verify_google_token


class FakeResponse:
    def __init__(self, data: object, status_code: int = 200) -> None:
        self._data = data
        self.status_code = status_code

    def json(self) -> object:
        return self._data

    def raise_for_status(self) -> None:
        return None


class FakeClient:
    def __init__(self, *, gets: list[FakeResponse], posts: list[FakeResponse] | None = None) -> None:
        self.gets = gets
        self.posts = posts or []

    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def get(self, *_args: object, **_kwargs: object) -> FakeResponse:
        return self.gets.pop(0)

    async def post(self, *_args: object, **_kwargs: object) -> FakeResponse:
        return self.posts.pop(0)


def _client_factory(clients: list[FakeClient]):
    def factory(*_args: object, **_kwargs: object) -> FakeClient:
        return clients.pop(0)

    return factory


@pytest.mark.asyncio
async def test_google_always_validates_audience() -> None:
    response = FakeResponse({"email": "user@example.com", "email_verified": True, "sub": "123", "aud": "other-app"})
    settings = SimpleNamespace(google_client_id="expected-app", google_client_secret="secret")
    with (
        patch("app.auth.oauth.get_settings", return_value=settings),
        patch("app.auth.oauth.httpx.AsyncClient", _client_factory([FakeClient(gets=[response])])),
    ):
        with pytest.raises(OAuthVerificationError, match="not issued for this application"):
            await verify_google_token("token")


@pytest.mark.asyncio
async def test_google_rejects_string_false_email_verification() -> None:
    response = FakeResponse(
        {
            "email": "user@example.com",
            "email_verified": "false",
            "sub": "123",
            "aud": "app",
        }
    )
    settings = SimpleNamespace(google_client_id="app", google_client_secret="secret")
    with (
        patch("app.auth.oauth.get_settings", return_value=settings),
        patch("app.auth.oauth.httpx.AsyncClient", _client_factory([FakeClient(gets=[response])])),
    ):
        with pytest.raises(OAuthVerificationError, match="Email is not verified"):
            await verify_google_token("token")


@pytest.mark.asyncio
async def test_github_requires_application_binding() -> None:
    settings = SimpleNamespace(gh_client_id="client", gh_client_secret="secret")
    clients = [
        FakeClient(gets=[FakeResponse({"id": 7, "login": "octocat"})]),
        FakeClient(gets=[], posts=[FakeResponse({}, status_code=404)]),
    ]
    with (
        patch("app.auth.oauth.get_settings", return_value=settings),
        patch("app.auth.oauth.httpx.AsyncClient", _client_factory(clients)),
    ):
        with pytest.raises(OAuthVerificationError, match="not issued for this application"):
            await verify_github_token("token")


@pytest.mark.asyncio
async def test_github_uses_verified_primary_email() -> None:
    settings = SimpleNamespace(gh_client_id="client", gh_client_secret="secret")
    clients = [
        FakeClient(gets=[FakeResponse({"id": 7, "name": "Octo", "avatar_url": "https://img"})]),
        FakeClient(
            gets=[
                FakeResponse(
                    [
                        {"email": "other@example.com", "primary": False, "verified": True},
                        {"email": "primary@example.com", "primary": True, "verified": True},
                    ]
                )
            ],
            posts=[FakeResponse({})],
        ),
    ]
    with (
        patch("app.auth.oauth.get_settings", return_value=settings),
        patch("app.auth.oauth.httpx.AsyncClient", _client_factory(clients)),
    ):
        verified = await verify_github_token("token")
    assert verified.email == "primary@example.com"


@pytest.mark.asyncio
async def test_github_rejects_unverified_primary_email() -> None:
    settings = SimpleNamespace(gh_client_id="client", gh_client_secret="secret")
    clients = [
        FakeClient(gets=[FakeResponse({"id": 7})]),
        FakeClient(
            gets=[FakeResponse([{"email": "primary@example.com", "primary": True, "verified": False}])],
            posts=[FakeResponse({})],
        ),
    ]
    with (
        patch("app.auth.oauth.get_settings", return_value=settings),
        patch("app.auth.oauth.httpx.AsyncClient", _client_factory(clients)),
    ):
        with pytest.raises(OAuthVerificationError, match="no verified primary email"):
            await verify_github_token("token")
