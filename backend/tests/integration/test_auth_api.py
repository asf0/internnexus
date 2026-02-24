"""Integration tests for auth API endpoints."""

import pytest
from datetime import datetime, timezone


class TestAuthAPI:
    """Test suite for authentication API endpoints."""

    @pytest.mark.asyncio
    async def test_register_success(self, client):
        """Test successful user registration."""
        # Arrange
        register_data = {
            "email": "test@example.com",
            "password": "SecurePass123!",
            "name": "Test User",
        }

        # Act
        response = await client.post("/auth/register", json=register_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "test@example.com"
        assert len(data["access_token"]) > 50  # JWT tokens are long

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client):
        """Test registration with weak password fails validation."""
        # Arrange
        register_data = {
            "email": "test@example.com",
            "password": "weak",  # Too short, missing requirements
            "name": "Test User",
        }

        # Act
        response = await client.post("/auth/register", json=register_data)

        # Assert
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client):
        """Test registration with invalid email fails."""
        # Arrange
        register_data = {"email": "not-an-email", "password": "SecurePass123!", "name": "Test User"}

        # Act
        response = await client.post("/auth/register", json=register_data)

        # Assert
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        """Test successful user login."""
        # Arrange - First register a user
        register_data = {
            "email": "logintest@example.com",
            "password": "SecurePass123!",
            "name": "Login Test User",
        }
        await client.post("/auth/register", json=register_data)

        # Act - Now login
        login_data = {"email": "logintest@example.com", "password": "SecurePass123!"}
        response = await client.post("/auth/login", json=login_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "logintest@example.com"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        # Arrange - First register a user
        register_data = {
            "email": "wrongpass@example.com",
            "password": "SecurePass123!",
            "name": "Wrong Pass User",
        }
        await client.post("/auth/register", json=register_data)

        # Act - Try to login with wrong password
        login_data = {"email": "wrongpass@example.com", "password": "WrongPass123!"}
        response = await client.post("/auth/login", json=login_data)

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_oauth_callback_invalid_provider(self, client):
        """Test OAuth callback with invalid provider."""
        # Arrange
        oauth_data = {
            "provider": "invalid-provider",  # Not google or github
            "provider_account_id": "12345",
            "email": "test@example.com",
            "access_token": "token",
        }

        # Act
        response = await client.post("/auth/oauth/callback", json=oauth_data)

        # Assert
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_oauth_callback_verification_failed(self, client):
        """Test OAuth callback when token verification fails."""
        # Arrange
        oauth_data = {
            "provider": "google",
            "provider_account_id": "12345",
            "email": "test@gmail.com",
            "access_token": "invalid-token",
        }

        # Act
        response = await client.post("/auth/oauth/callback", json=oauth_data)

        # Assert
        assert response.status_code == 401
        assert "OAUTH_VERIFICATION_FAILED" in str(response.json())

    @pytest.mark.asyncio
    async def test_set_password_too_short(self, client):
        """Test setting password that is too short."""
        # Arrange
        password_data = {
            "password": "short"  # Less than 8 characters
        }

        # Act
        response = await client.post("/auth/set-password", json=password_data)

        # Assert
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client):
        """Test registration with duplicate email fails."""
        # Arrange
        register_data = {
            "email": "duplicate@example.com",
            "password": "SecurePass123!",
            "name": "First User",
        }
        # First registration
        await client.post("/auth/register", json=register_data)

        # Act - Try to register again with same email
        register_data["name"] = "Second User"
        response = await client.post("/auth/register", json=register_data)

        # Assert
        assert response.status_code == 409  # Conflict

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        # Arrange
        login_data = {"email": "nonexistent@example.com", "password": "SomePass123!"}

        # Act
        response = await client.post("/auth/login", json=login_data)

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_set_password_unauthorized(self, client):
        """Test setting password without authentication fails."""
        # Arrange
        password_data = {"password": "NewSecurePass123!"}

        # Act
        response = await client.post("/auth/set-password", json=password_data)

        # Assert
        assert response.status_code == 401  # Unauthorized - requires auth token
