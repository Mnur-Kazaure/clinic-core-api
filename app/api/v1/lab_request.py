# app/api/v1/lab_request.py
from fastapi import APIRouter, Depends, status
from app.schemas.lab_request import LabRequestCreate, LabRequestResponse
from app.core.guards.lab_request_guard import require_lab_request_permission
from app.services.lab_request_service import LabRequestService
from app.core.dependencies import get_db
from app.core.auth import get_current_user

router = APIRouter(prefix="/lab", tags=["Lab"])


@router.post(
    "/requests",
    response_model=LabRequestResponse,
    status_code=status.HTTP_201_CREATED,
)


def create_lab_request(
    payload: LabRequestCreate,
    visit=Depends(require_lab_request_permission),
    db=Depends(get_db),
    user=Depends(get_current_user),
):


# def create_lab_request(
#     payload: LabRequestCreate,
#     visit=Depends(require_lab_request_permission),
#     db=Depends(get_db),
#     user=Depends(get_current_user),
# ):
    service = LabRequestService(db)

    return service.create_request(
        visit=visit,
        test_name=payload.test_name,
        doctor_id=user.id,
    )