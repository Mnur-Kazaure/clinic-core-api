# app/core/auth/passwords.py
from passlib.context import CryptContext

# Central password context
_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(plain_password: str) -> str:
    """
    One-way hash for password storage.
    Safe to store in DB.
    """
    return _pwd_context.hash(plain_password)


def verify_password(
    plain_password: str,
    password_hash: str,
) -> bool:
    """
    Constant-time password verification.
    Returns True / False only.
    """
    return _pwd_context.verify(plain_password, password_hash)
