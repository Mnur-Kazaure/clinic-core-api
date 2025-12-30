# app/core/rbac.py
from fastapi import Depends, HTTPException, status
from app.shared.enums import UserRole
# app/core/dependencies.py
from app.core.dependencies import get_current_user



VISIT_ACCESS_ROLES = {
    UserRole.RECEPTION,
    UserRole.DOCTOR,
    UserRole.LAB,
    UserRole.PHARMACY,
    UserRole.ADMIN,
}


def require_visit_access(user=Depends(get_current_user)):
    # 🔒 Internal system bypass (not HTTP-facing)
    if user.role == UserRole.SYSTEM:
        return user

    if user.role not in VISIT_ACCESS_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not allowed to access visit operations",
        )
    return user



# Reception role required
def require_reception(user=Depends(get_current_user)):
    if user.role != UserRole.RECEPTION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reception access required",
        )
    return user