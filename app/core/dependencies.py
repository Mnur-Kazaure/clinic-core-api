# app/core/dependencies.py
#from typing import Generator
from sqlalchemy.orm import Session

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.core.auth.jwt import decode_access_token
from app.models.user import User



# def get_db() -> Generator[Session, None, None]: # Seems deplicated with app/core/database.py
#     from app.core.database import SessionLocal  # 🔑 lazy import

#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()



oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")  # placeholder


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve JWT → User identity.

    Responsibilities:
    - Decode token
    - Validate required claims
    - Load user from DB
    - Return User ORM

    No RBAC.
    No permissions.
    No business logic.
    """
    try:
        payload = decode_access_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    try:
        user_id = UUID(payload.get("sub"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
