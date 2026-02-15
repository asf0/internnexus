from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64
import secrets
# Generate RSA key pair
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend(),
)
public_key = private_key.public_key()
# Export as PEM
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode('utf-8')
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode('utf-8')
# Encode to base64
private_b64 = base64.b64encode(private_pem.encode('utf-8')).decode('utf-8')
public_b64 = base64.b64encode(public_pem.encode('utf-8')).decode('utf-8')
# Generate auth secret
auth_secret = secrets.token_urlsafe(32)
print("=== AUTH_SECRET ===")
print(auth_secret)
print()
print("=== OAUTH_ENCRYPTION_PUBLIC_KEY_B64 ===")
print(public_b64)
print()
print("=== OAUTH_ENCRYPTION_PRIVATE_KEY_B64 ===")
print(private_b64)