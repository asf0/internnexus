"""RSA+AES hybrid encryption for OAuth tokens."""

from __future__ import annotations

import base64
import logging
import os
import secrets
from typing import Any
import base64

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

logger = logging.getLogger(__name__)

AES_KEY_SIZE = 32
AES_IV_SIZE = 16


class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""

    pass


class TokenEncryptor:
    """RSA+AES hybrid encryption for sensitive tokens.

    Uses RSA to encrypt a randomly generated AES key, then AES-CBC to encrypt
    the actual data. This allows for secure storage of OAuth tokens in the database.

    The hybrid approach combines:
    - RSA's ability to securely exchange keys (encrypt the AES key with RSA public key)
    - AES's efficiency for encrypting arbitrary-length data
    """

    def __init__(self, public_key_pem: str, private_key_pem: str | None = None) -> None:
        """Initialize the encryptor with RSA keys.

        Args:
            public_key_pem: PEM-encoded RSA public key (required for encryption)
            private_key_pem: PEM-encoded RSA private key (required for decryption)
        """
        self._public_key = self._load_public_key(public_key_pem)
        self._private_key = None
        if private_key_pem:
            self._private_key = self._load_private_key(private_key_pem)

    def _load_public_key(self, pem: str) -> Any:
        """Load RSA public key from PEM string."""
        if not pem or not pem.strip():
            raise EncryptionError("Public key is empty or not configured")

        pem = pem.strip()

        try:
            if not pem.startswith("-----BEGIN"):
                pem = base64.b64decode(pem).decode("utf-8")

            pem = pem.replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")

            return serialization.load_pem_public_key(
                pem.encode("utf-8"),
                backend=default_backend(),
            )
        except Exception as exc:
            raise EncryptionError(f"Failed to load public key: {exc}") from exc

    def _load_private_key(self, pem: str) -> Any:
        """Load RSA private key from PEM string."""
        if not pem or not pem.strip():
            raise EncryptionError("Private key is empty or not configured")

        pem = pem.strip()

        try:
            if not pem.startswith("-----BEGIN"):
                pem = base64.b64decode(pem).decode("utf-8")

            pem = pem.replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")

            return serialization.load_pem_private_key(
                pem.encode("utf-8"),
                password=None,
                backend=default_backend(),
            )
        except Exception as exc:
            raise EncryptionError(f"Failed to load private key: {exc}") from exc

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string using RSA+AES hybrid encryption.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64-encoded encrypted data (encrypted_aes_key + iv + ciphertext)

        Raises:
            EncryptionError: If encryption fails
        """
        if not plaintext:
            return ""

        try:
            aes_key = secrets.token_bytes(AES_KEY_SIZE)
            iv = secrets.token_bytes(AES_IV_SIZE)

            encrypted_aes_key = self._public_key.encrypt(
                aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            plaintext_bytes = plaintext.encode("utf-8")
            padded_plaintext = self._pkcs7_pad(plaintext_bytes, AES_KEY_SIZE)

            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()

            result = encrypted_aes_key + iv + ciphertext
            return base64.b64encode(result).decode("utf-8")

        except Exception as exc:
            raise EncryptionError(f"Encryption failed: {exc}") from exc

    def decrypt(self, ciphertext_b64: str) -> str:
        """Decrypt a string using RSA+AES hybrid encryption.

        Args:
            ciphertext_b64: Base64-encoded encrypted data

        Returns:
            Decrypted plaintext string

        Raises:
            EncryptionError: If decryption fails or private key not available
        """
        if not ciphertext_b64:
            return ""

        if self._private_key is None:
            raise EncryptionError("Private key not available for decryption")

        try:
            encrypted_data = base64.b64decode(ciphertext_b64)

            rsa_key_size = self._private_key.key_size // 8
            encrypted_aes_key = encrypted_data[:rsa_key_size]
            iv = encrypted_data[rsa_key_size : rsa_key_size + AES_IV_SIZE]
            ciphertext = encrypted_data[rsa_key_size + AES_IV_SIZE :]

            aes_key = self._private_key.decrypt(
                encrypted_aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            plaintext = self._pkcs7_unpad(padded_plaintext)
            return plaintext.decode("utf-8")

        except Exception as exc:
            raise EncryptionError(f"Decryption failed: {exc}") from exc

    @staticmethod
    def _pkcs7_pad(data: bytes, block_size: int) -> bytes:
        """Apply PKCS7 padding."""
        padding_length = block_size - (len(data) % block_size)
        return data + bytes([padding_length] * padding_length)

    @staticmethod
    def _pkcs7_unpad(data: bytes) -> bytes:
        """Remove PKCS7 padding."""
        padding_length = data[-1]
        return data[:-padding_length]


def generate_rsa_key_pair(key_size: int = 2048) -> tuple[str, str]:
    """Generate a new RSA key pair for token encryption.

    Args:
        key_size: RSA key size in bits (default: 2048)

    Returns:
        Tuple of (public_key_pem, private_key_pem)
    """
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend(),
    )

    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return public_pem, private_pem


_encryptor_instance: TokenEncryptor | None = None


def get_encryptor() -> TokenEncryptor:
    """Get or create the global encryptor instance.

    Raises:
        EncryptionError: If encryption keys are not configured
    """
    global _encryptor_instance

    if _encryptor_instance is None:
        from app.config import get_settings

        settings = get_settings()

        if not settings.oauth_encryption_public_key_b64:
            raise EncryptionError("OAuth encryption public key not configured")

        _encryptor_instance = TokenEncryptor(
            public_key_pem=settings.oauth_encryption_public_key_b64,
            private_key_pem=settings.oauth_encryption_private_key_b64,
        )

    return _encryptor_instance


def encrypt_token(plaintext: str) -> str:
    """Encrypt a token string.

    Args:
        plaintext: Token to encrypt

    Returns:
        Base64-encoded encrypted token
    """
    if not plaintext:
        return ""
    return get_encryptor().encrypt(plaintext)


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a token string.

    Args:
        ciphertext: Base64-encoded encrypted token

    Returns:
        Decrypted token
    """
    if not ciphertext:
        return ""
    return get_encryptor().decrypt(ciphertext)
