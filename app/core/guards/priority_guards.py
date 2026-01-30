# app/core/guards/priority_guards.py
from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user
from app.shared.enums import UserRole


PRIORITY_ROLES = {
    UserRole.RECEPTION,
    UserRole.DOCTOR,
    UserRole.CLINIC_ADMIN,
}


def require_priority_role(user=Depends(get_current_user)):
    if user.role not in PRIORITY_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Priority access denied",
        )
    return user
