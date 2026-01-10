from fastapi import HTTPException, status
from app.shared.enums import UserRole


def require_reception_role(current_user):
    """
    Ensure the current user has RECEPTION role.
    """
    if current_user.role != UserRole.RECEPTION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Reception may create patients",
        )
