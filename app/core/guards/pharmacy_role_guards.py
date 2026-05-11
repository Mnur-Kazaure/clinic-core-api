from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user
from app.shared.enums import UserRole


HOD_DASHBOARD_ROLES = {
    UserRole.PHARMACY_HOD,
}

CMD_DASHBOARD_ROLES = {
    UserRole.CMD,
}

STORE_DASHBOARD_ROLES = {
    UserRole.PHARMACY_STORE_OFFICER,
}

INVENTORY_READ_ROLES = set(STORE_DASHBOARD_ROLES)
INVENTORY_WRITE_ROLES = set(STORE_DASHBOARD_ROLES)


def require_pharmacy_inventory_read_user(current_user=Depends(get_current_user)):
    if current_user.role not in INVENTORY_READ_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pharmacy inventory read access denied",
        )
    return current_user


def require_pharmacy_inventory_write_user(current_user=Depends(get_current_user)):
    if current_user.role not in INVENTORY_WRITE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pharmacy inventory write access denied",
        )
    return current_user


def require_pharmacy_inventory_manage_user(current_user=Depends(get_current_user)):
    if current_user.role not in HOD_DASHBOARD_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pharmacy HOD inventory management access denied",
        )
    return current_user


def require_pharmacy_hod_dashboard_user(current_user=Depends(get_current_user)):
    if current_user.role not in HOD_DASHBOARD_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pharmacy HOD access required",
        )
    return current_user


def require_cmd_dashboard_user(current_user=Depends(get_current_user)):
    if current_user.role not in CMD_DASHBOARD_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CMD access required",
        )
    return current_user


def require_pharmacy_store_dashboard_user(current_user=Depends(get_current_user)):
    if current_user.role not in STORE_DASHBOARD_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pharmacy Store Officer access required",
        )
    return current_user
