# app/core/auth_dev.py
from fastapi import Header, HTTPException, status
from uuid import UUID
from app.shared.enums import UserRole


class FakeUser:
    def __init__(self, id: UUID, role: UserRole, clinic_id: UUID):
        self.id = id
        self.role = role
        self.clinic_id = clinic_id


def get_current_user(
    x_user_role: str = Header(...),
    x_user_id: str = Header(...),
    x_clinic_id: str = Header(...),
):
    try:
        return FakeUser(
            id=UUID(x_user_id),
            role=UserRole(x_user_role),
            clinic_id=UUID(x_clinic_id),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid identity headers",
        )