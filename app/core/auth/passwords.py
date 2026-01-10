# app/core/auth/passwords.py
from passlib.context import CryptContext

_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

MAX_BCRYPT_BYTES = 72  # bcrypt max

def hash_password(plain_password: str) -> str:
    """
    Hash a password safely for bcrypt.
    Truncate to 72 bytes (UTF-8) to avoid ValueError.
    Preserves valid UTF-8 characters.
    """
    # Encode, truncate bytes, then decode safely
    encoded = plain_password.encode("utf-8")
    truncated = encoded[:MAX_BCRYPT_BYTES].decode("utf-8", errors="replace")
    return _pwd_context.hash(truncated)

def verify_password(plain_password: str, password_hash: str) -> bool:
    """
    Verify a password safely for bcrypt.
    """
    encoded = plain_password.encode("utf-8")
    truncated = encoded[:MAX_BCRYPT_BYTES].decode("utf-8", errors="replace")
    return _pwd_context.verify(truncated, password_hash)
