# # app/api/v1/patient.py
from fastapi import APIRouter, Depends, status, HTTPException, Query

from app.schemas.patient import PatientCreateSchema, PatientReadSchema
from app.services.patient_service import PatientService
from app.services.access_log_service import AccessLogService
from app.core.dependencies import get_db
from app.core.rbac import require_reception

router = APIRouter(prefix="/patient", tags=["Patient"])


@router.post(
    "",
    response_model=PatientReadSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_patient(
    payload: PatientCreateSchema,
    db=Depends(get_db),
    current_user=Depends(require_reception),
):
    service = PatientService(db)
    return service.create_patient(payload, current_user)


@router.get(
    "/search",
    response_model=list[PatientReadSchema],
    status_code=status.HTTP_200_OK,
)
def search_patients(
    q: str | None = None,
    full_name: str | None = None,
    phone_number: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    purpose_of_use: str = Query(..., min_length=2),
    reason: str = Query(..., min_length=2),
    db=Depends(get_db),
    current_user=Depends(require_reception),
):
    service = PatientService(db)
    try:
        AccessLogService(db).log_search(
            actor=current_user,
            clinic_id=current_user.clinic_id,
            purpose_of_use=purpose_of_use,
            reason=reason,
        )
        return service.search_patients(
            clinic_id=current_user.clinic_id,
            q=q,
            full_name=full_name,
            phone_number=phone_number,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )



# from fastapi import APIRouter, Depends, status

# from app.schemas.patient import PatientCreateSchema, PatientReadSchema
# from app.services.patient_service import PatientService
# from app.core.dependencies import get_db
# # from app.core.auth import get_current_user
# from app.core.rbac import require_reception

# router = APIRouter(prefix="/patient", tags=["Patient"])


# @router.post(
#     "",
#     response_model=PatientReadSchema,
#     status_code=status.HTTP_201_CREATED,
# )
# def create_patient(
#     payload: PatientCreateSchema,
#     db=Depends(get_db),
#     current_user=Depends(require_reception),
# #    current_user=Depends(get_current_user),
# ):
#     service = PatientService(db)
#     return service.create_patient(payload, current_user)
