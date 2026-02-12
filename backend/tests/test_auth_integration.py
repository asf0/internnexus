"""Integration tests for authentication flow."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User


class TestAuthFlow:
    """Test complete authentication flows."""

    def test_complete_registration_and_login_flow(self, client: TestClient, db_session: Session):
        """Test complete flow: register then login."""
        # Step 1: Register
        register_response = client.post(
            "/auth/register",
            json={
                "email": "flowtest@example.com",
                "password": "StrongPass1!",
                "name": "Flow Test User",
            },
        )

        assert register_response.status_code == 200
        register_data = register_response.json()
        assert "access_token" in register_data

        # Step 2: Login with same credentials
        login_response = client.post(
            "/auth/login",
            json={
                "email": "flowtest@example.com",
                "password": "StrongPass1!",
            },
        )

        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "access_token" in login_data
        assert login_data["user"]["email"] == "flowtest@example.com"

    def test_oauth_then_set_password_flow(self, client: TestClient, db_session: Session):
        """Test OAuth login followed by setting a password."""
        from datetime import datetime, timezone

        # Step 1: OAuth callback (creates user)
        oauth_response = client.post(
            "/auth/oauth/callback",
            json={
                "provider": "github",
                "provider_account_id": "flow_test_123",
                "email": "oauthflow@example.com",
                "name": "OAuth Flow User",
                "access_token": "github_token",
            },
        )

        assert oauth_response.status_code == 200
        oauth_data = oauth_response.json()
        token = oauth_data["access_token"]

        # Step 2: Try to login with password (should fail)
        login_response = client.post(
            "/auth/login",
            json={
                "email": "oauthflow@example.com",
                "password": "AnyPass1!",
            },
        )

        assert login_response.status_code == 401

        # Step 3: Set password
        set_password_response = client.post(
            "/auth/set-password",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "NewStrongPass1!"},
        )

        assert set_password_response.status_code == 200

        # Step 4: Now login with password should work
        login_response2 = client.post(
            "/auth/login",
            json={
                "email": "oauthflow@example.com",
                "password": "NewStrongPass1!",
            },
        )

        assert login_response2.status_code == 200
        assert "access_token" in login_response2.json()

    def test_cannot_register_with_existing_oauth_email(
        self, client: TestClient, db_session: Session
    ):
        """Test that OAuth users can't be registered again."""
        from datetime import datetime, timezone

        # Step 1: Create OAuth user
        oauth_response = client.post(
            "/auth/oauth/callback",
            json={
                "provider": "google",
                "provider_account_id": "google_123",
                "email": "protected@example.com",
                "name": "Protected User",
                "access_token": "token",
            },
        )

        assert oauth_response.status_code == 200

        # Step 2: Try to register with same email
        register_response = client.post(
            "/auth/register",
            json={
                "email": "protected@example.com",
                "password": "StrongPass1!",
                "name": "Imposter",
            },
        )

        assert register_response.status_code == 409
        data = register_response.json()
        assert data["detail"]["error"] == "EMAIL_REGISTERED_WITH_OAUTH"

    def test_token_renewal_after_set_password(self, client: TestClient, db_session: Session):
        """Test that setting password returns a new valid token."""
        from datetime import datetime, timezone

        # Create OAuth user
        oauth_response = client.post(
            "/auth/oauth/callback",
            json={
                "provider": "github",
                "provider_account_id": "renewal_test",
                "email": "renewal@example.com",
                "access_token": "token",
            },
        )

        old_token = oauth_response.json()["access_token"]

        # Set password (should return new token)
        set_password_response = client.post(
            "/auth/set-password",
            headers={"Authorization": f"Bearer {old_token}"},
            json={"password": "NewPass1!"},
        )

        assert set_password_response.status_code == 200
        new_token = set_password_response.json()["access_token"]

        # New token should be different
        assert new_token != old_token

        # New token should work for authenticated requests
        # (Assuming there's a protected endpoint to test with)
        # For now, we'll just verify it's a valid JWT format
        assert len(new_token.split(".")) == 3  # JWT has 3 parts
