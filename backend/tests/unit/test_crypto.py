"""Unit tests for crypto module - RSA+AES hybrid encryption."""

import base64
import pytest
from unittest.mock import Mock, patch

from app.auth.crypto import (
    TokenEncryptor,
    EncryptionError,
    generate_rsa_key_pair,
    get_encryptor,
    encrypt_token,
)


class TestTokenEncryptor:
    """Test suite for TokenEncryptor class."""

    @pytest.fixture
    def key_pair(self):
        """Generate a test RSA key pair."""
        return generate_rsa_key_pair(key_size=2048)

    @pytest.fixture
    def encryptor(self, key_pair):
        """Create a TokenEncryptor with test keys."""
        public_key, private_key = key_pair
        return TokenEncryptor(public_key_pem=public_key, private_key_pem=private_key)

    def test_encrypt_decrypt_roundtrip(self, encryptor):
        """Test that encryption and decryption are inverse operations."""
        # Arrange
        plaintext = "test-oauth-token-12345"

        # Act
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        # Assert
        assert encrypted != plaintext
        assert decrypted == plaintext

    def test_encrypt_empty_string(self, encryptor):
        """Test that empty string returns empty string."""
        # Act
        result = encryptor.encrypt("")

        # Assert
        assert result == ""

    def test_decrypt_empty_string(self, encryptor):
        """Test that decrypting empty string returns empty string."""
        # Act
        result = encryptor.decrypt("")

        # Assert
        assert result == ""

    def test_encrypt_unicode(self, encryptor):
        """Test encryption of unicode characters."""
        # Arrange
        plaintext = "Hello 世界 🌍 üñíçödé"

        # Act
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        # Assert
        assert decrypted == plaintext

    def test_encrypt_long_text(self, encryptor):
        """Test encryption of long text."""
        # Arrange
        plaintext = "x" * 10000

        # Act
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        # Assert
        assert decrypted == plaintext

    def test_decrypt_without_private_key(self, key_pair):
        """Test that decryption fails without private key."""
        # Arrange
        public_key, _ = key_pair
        encryptor = TokenEncryptor(public_key_pem=public_key, private_key_pem=None)
        encrypted = encryptor.encrypt("test")

        # Act & Assert
        with pytest.raises(EncryptionError, match="Private key not available"):
            encryptor.decrypt(encrypted)

    def test_invalid_public_key(self):
        """Test that invalid public key raises error."""
        # Act & Assert
        with pytest.raises(EncryptionError, match="Failed to load public key"):
            TokenEncryptor(public_key_pem="invalid-key", private_key_pem=None)

    def test_invalid_private_key(self, key_pair):
        """Test that invalid private key raises error."""
        # Act & Assert
        with pytest.raises(EncryptionError, match="Failed to load private key"):
            TokenEncryptor(public_key_pem=key_pair[0], private_key_pem="invalid-key")

    def test_empty_public_key(self):
        """Test that empty public key raises error."""
        # Act & Assert
        with pytest.raises(EncryptionError, match="Public key is empty"):
            TokenEncryptor(public_key_pem="", private_key_pem=None)

    def test_base64_encoded_key(self, key_pair):
        """Test that base64-encoded keys work."""
        # Arrange
        public_key, private_key = key_pair
        public_key_b64 = base64.b64encode(public_key.encode()).decode()
        private_key_b64 = base64.b64encode(private_key.encode()).decode()

        # Act
        encryptor = TokenEncryptor(
            public_key_pem=public_key_b64,
            private_key_pem=private_key_b64,
        )
        encrypted = encryptor.encrypt("test")
        decrypted = encryptor.decrypt(encrypted)

        # Assert
        assert decrypted == "test"

    def test_decrypt_invalid_base64(self, encryptor):
        """Test that invalid base64 raises error."""
        # Act & Assert
        with pytest.raises(EncryptionError):
            encryptor.decrypt("not-valid-base64!!!")

    def test_pkcs7_padding(self, encryptor):
        """Test PKCS7 padding with various block sizes."""
        # Test various lengths to ensure padding works correctly
        for length in [1, 15, 16, 17, 31, 32, 33, 47, 48, 49]:
            plaintext = "x" * length
            encrypted = encryptor.encrypt(plaintext)
            decrypted = encryptor.decrypt(encrypted)
            assert decrypted == plaintext


class TestGenerateRSAKeyPair:
    """Test suite for RSA key pair generation."""

    def test_generate_key_pair(self):
        """Test that key pair generation produces valid keys."""
        # Act
        public_key, private_key = generate_rsa_key_pair()

        # Assert
        assert public_key.startswith("-----BEGIN PUBLIC KEY-----")
        assert public_key.endswith("-----END PUBLIC KEY-----\n")
        assert private_key.startswith("-----BEGIN PRIVATE KEY-----")
        assert private_key.endswith("-----END PRIVATE KEY-----\n")

    def test_generate_key_pair_different_keys(self):
        """Test that each call generates different keys."""
        # Act
        pair1 = generate_rsa_key_pair()
        pair2 = generate_rsa_key_pair()

        # Assert
        assert pair1[0] != pair2[0]
        assert pair1[1] != pair2[1]

    def test_generate_key_pair_with_size(self):
        """Test key generation with different sizes."""
        # Act
        public_key, private_key = generate_rsa_key_pair(key_size=1024)

        # Assert - keys should still be valid
        assert "BEGIN PUBLIC KEY" in public_key
        assert "BEGIN PRIVATE KEY" in private_key


class TestGetEncryptor:
    """Test suite for get_encryptor function."""

    @patch("app.auth.crypto.get_settings")
    def test_get_encryptor_success(self, mock_get_settings):
        """Test successful creation of global encryptor."""
        # Arrange
        public_key, private_key = generate_rsa_key_pair()
        mock_settings = Mock()
        mock_settings.oauth_encryption_public_key_b64 = public_key
        mock_settings.oauth_encryption_private_key_b64 = private_key
        mock_get_settings.return_value = mock_settings

        # Clear any cached instance
        import app.auth.crypto as crypto_module

        crypto_module._encryptor_instance = None

        # Act
        encryptor = get_encryptor()

        # Assert
        assert encryptor is not None

    @patch("app.auth.crypto.get_settings")
    def test_get_encryptor_no_public_key(self, mock_get_settings):
        """Test that missing public key raises error."""
        # Arrange
        mock_settings = Mock()
        mock_settings.oauth_encryption_public_key_b64 = None
        mock_get_settings.return_value = mock_settings

        # Clear any cached instance
        import app.auth.crypto as crypto_module

        crypto_module._encryptor_instance = None

        # Act & Assert
        with pytest.raises(EncryptionError, match="OAuth encryption public key not configured"):
            get_encryptor()

    @patch("app.auth.crypto.get_settings")
    def test_get_encryptor_caching(self, mock_get_settings):
        """Test that encryptor is cached and reused."""
        # Arrange
        public_key, private_key = generate_rsa_key_pair()
        mock_settings = Mock()
        mock_settings.oauth_encryption_public_key_b64 = public_key
        mock_settings.oauth_encryption_private_key_b64 = private_key
        mock_get_settings.return_value = mock_settings

        # Clear any cached instance
        import app.auth.crypto as crypto_module

        crypto_module._encryptor_instance = None

        # Act
        encryptor1 = get_encryptor()
        encryptor2 = get_encryptor()

        # Assert - should be same instance
        assert encryptor1 is encryptor2
        mock_get_settings.assert_called_once()


class TestEncryptToken:
    """Test suite for encrypt_token convenience function."""

    @patch("app.auth.crypto.get_encryptor")
    def test_encrypt_token_success(self, mock_get_encryptor):
        """Test successful token encryption."""
        # Arrange
        mock_encryptor = Mock()
        mock_encryptor.encrypt.return_value = "encrypted-token"
        mock_get_encryptor.return_value = mock_encryptor

        # Act
        result = encrypt_token("test-token")

        # Assert
        assert result == "encrypted-token"
        mock_encryptor.encrypt.assert_called_once_with("test-token")

    @patch("app.auth.crypto.get_encryptor")
    def test_encrypt_token_empty(self, mock_get_encryptor):
        """Test that empty token returns empty string."""
        # Arrange
        mock_encryptor = Mock()
        mock_get_encryptor.return_value = mock_encryptor

        # Act
        result = encrypt_token("")

        # Assert
        assert result == ""
        mock_encryptor.encrypt.assert_not_called()

    @patch("app.auth.crypto.get_encryptor")
    def test_encrypt_token_none(self, mock_get_encryptor):
        """Test that None token returns empty string."""
        # Arrange
        mock_encryptor = Mock()
        mock_get_encryptor.return_value = mock_encryptor

        # Act
        result = encrypt_token(None)

        # Assert
        assert result == ""
        mock_encryptor.encrypt.assert_not_called()
