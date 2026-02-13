# app/core/guards/priority_guards.py
from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user
from app.shared.enums import UserRole


PRIORITY_ROLES = {
    UserRole.DOCTOR,
    UserRole.CHEW,
    UserRole.MIDWIFE,
}


def require_priority_role(user=Depends(get_current_user)):
    role_value = user.role.value if isinstance(user.role, UserRole) else str(user.role).replace("UserRole.", "")
    allowed = {role.value for role in PRIORITY_ROLES}
    if role_value not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Priority access denied",
        )
    return user
