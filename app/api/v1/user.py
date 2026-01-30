# app/api/v1/user.py
from fastapi import APIRouter, Depends

from app.core.dependencies import get_db
from app.core.rbac import require_reception
from app.schemas.user import DoctorListSchema
from app.services.user_service import UserService


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
