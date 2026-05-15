from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user
from app.shared.enums import UserRole


ACCOUNTANT_READ_ROLES = {
    UserRole.ACCOUNTANT,
    UserRole.CLINIC_ADMIN,
    UserRole.ADMIN,
}

FINANCE_MANAGER_ROLES = {
    UserRole.CLINIC_ADMIN,
    UserRole.ADMIN,
}


def require_accountant_read_role(user=Depends(get_current_user)):
    if user.role not in ACCOUNTANT_READ_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accountant dashboard access denied",
        )
    return user


def require_finance_manager_role(user=Depends(get_current_user)):
    if user.role not in FINANCE_MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Finance manager privileges required",
        )
    return user

