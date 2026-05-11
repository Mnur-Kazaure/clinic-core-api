# app/api/v1/user.py
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_db
from app.core.rbac import require_reception, require_visit_access
from app.schemas.user import DoctorListSchema
from app.services.user_service import UserService
from app.shared.enums import UserRole


router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/doctors",
    response_model=list[DoctorListSchema],
)
def list_doctors(
    db=Depends(get_db),
    current_user=Depends(require_reception),
):
    service = UserService(db)
    return service.list_doctors(current_user.clinic_id)


@router.get(
    "/chews",
    response_model=list[DoctorListSchema],
)
def list_chews(
    db=Depends(get_db),
    current_user=Depends(require_reception),
):
    service = UserService(db)
    return service.list_by_role(current_user.clinic_id, UserRole.CHEW)


@router.get(
    "/midwives",
    response_model=list[DoctorListSchema],
)
def list_midwives(
    db=Depends(get_db),
    current_user=Depends(require_reception),
):
    service = UserService(db)
    return service.list_by_role(current_user.clinic_id, UserRole.MIDWIFE)


@router.get(
    "/assignable",
    response_model=list[DoctorListSchema],
)
def list_assignable_staff(
    service_line_id: UUID | None = None,
    role: UserRole | None = None,
    include_all_departments: bool = False,
    department_id: UUID | None = None,
    db=Depends(get_db),
    current_user=Depends(require_visit_access),
):
    service = UserService(db)
    allowed_department_ids = getattr(current_user, "allowed_department_ids", None) or []
    if department_id is not None and allowed_department_ids and department_id not in allowed_department_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Department access denied",
        )
    effective_department_id = department_id or getattr(
        current_user,
        "current_department_id",
        None,
    )
    if current_user.role == UserRole.CHEW:
        return service.list_by_roles(
            current_user.clinic_id,
            [UserRole.CHEW, UserRole.MIDWIFE],
        )
    if current_user.role == UserRole.MIDWIFE:
        return service.list_by_roles(
            current_user.clinic_id,
            [UserRole.MIDWIFE, UserRole.CHEW],
        )
    if current_user.role == UserRole.DOCTOR:
        return service.list_assignable_staff(
            current_user.clinic_id,
            service_line_id=service_line_id,
            role_filter=UserRole.DOCTOR,
            department_id=effective_department_id,
            include_all_departments=include_all_departments,
        )
    if current_user.role in {UserRole.RECEPTION, UserRole.CLINIC_ADMIN, UserRole.ADMIN}:
        return service.list_assignable_staff(
            current_user.clinic_id,
            service_line_id=service_line_id,
            role_filter=role,
            department_id=effective_department_id,
            include_all_departments=include_all_departments,
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not allowed to list assignable staff",
    )
