# app/core/guards/bed_guards.py
from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user
from app.shared.enums import UserRole


BED_MANAGEMENT_ROLES = {
    UserRole.ADMIN,
    UserRole.CLINIC_ADMIN,
}


def require_bed_management_role(user=Depends(get_current_user)):
    if user.role not in BED_MANAGEMENT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bed management access denied",
        )
    return user
