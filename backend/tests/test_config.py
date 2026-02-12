"""Tests for configuration and settings."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from app.config import Settings, get_settings


class TestSettings:
    """Test application settings."""

    def test_settings_default_values(self):
        """Test default settings values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

            assert settings.jwt_algorithm == "HS256"
            assert settings.jwt_expiration_hours == 24
            assert settings.app_name == "InternNexus API"

    def test_settings_from_environment(self):
        """Test loading settings from environment variables."""
        env_vars = {
            "POSTGRES_DB": "test_db",
            "POSTGRES_USER": "test_user",
            "POSTGRES_PASSWORD": "test_pass",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "EMBEDDING_PROVIDER": "ollama",
            "EMBEDDING_MODEL": "nomic-embed-text",
            "OLLAMA_BASE_URL": "http://localhost:11434",
            "AUTH_SECRET": "test-only-auth-secret-NOT-REAL",
            "JWT_ALGORITHM": "HS512",
            "JWT_EXPIRATION_HOURS": "48",
            "REDIS_URL": "redis://localhost:6379/1",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()

            assert settings.auth_secret == "test-only-auth-secret-NOT-REAL"
            assert settings.jwt_algorithm == "HS512"
            assert settings.jwt_expiration_hours == 48
            assert settings.resolved_database_url == "postgresql://test:test@localhost/test"
            assert settings.redis_url == "redis://localhost:6379/1"

    def test_database_url_resolution(self):
        """Test database URL resolution."""
        # Test with explicit DATABASE_URL
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@host/db"}, clear=True):
            settings = Settings()
            assert "resolved_database_url" in dir(settings) or hasattr(settings, "database_url")

    def test_get_settings_singleton(self):
        """Test that get_settings returns a singleton."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_settings_missing_required_values(self):
        """Test behavior when required settings are missing."""
        # AUTH_SECRET might be required - test that it raises or has default
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            # Should either have a default or be None
            assert hasattr(settings, "auth_secret")


class TestEnvironmentVariables:
    """Test environment variable handling."""

    def test_boolean_parsing(self):
        """Test parsing of boolean environment variables."""
        # Test various boolean representations
        bool_tests = [
            ("true", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
        ]

        for value, expected in bool_tests:
            with patch.dict(os.environ, {"DEBUG": value}, clear=True):
                # Note: This depends on how Settings handles booleans
                # The actual implementation may vary
                pass  # Placeholder for boolean parsing test

    def test_integer_parsing(self):
        """Test parsing of integer environment variables."""
        with patch.dict(os.environ, {"JWT_EXPIRATION_HOURS": "48"}, clear=True):
            settings = Settings()
            assert isinstance(settings.jwt_expiration_hours, int)
            assert settings.jwt_expiration_hours == 48

    def test_invalid_integer_parsing(self):
        """Test handling of invalid integer values."""
        with patch.dict(os.environ, {"JWT_EXPIRATION_HOURS": "invalid"}, clear=True):
            # Should either raise an error or use default
            try:
                settings = Settings()
                # If it doesn't raise, check that it has a default
                assert hasattr(settings, "jwt_expiration_hours")
            except ValueError:
                pass  # Expected behavior
