from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth.contracts import AuthContext
from app.models.user import User


class DbAuthContext(AuthContext):
    """
    DB-backed AuthContext implementation.

    - Receives Session via DI
    - Resolves User from JWT claims
    - No session creation
    - Transaction-safe
    """

    def __init__(self, db: Session):
        self.db = db

    def resolve_user(self, claims: dict) -> User:
        try:
            user_id = UUID(claims["sub"])
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
            )

        user = (
            self.db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User inactive",
            )

        return user
