from fastapi import APIRouter, Depends, status

from app.core.auth import get_current_user
from app.core.dependencies import get_db
from app.schemas.follow_up import ChronicRecallCreateRequest, ChronicRecallResponse
from app.services.follow_up_service import ChronicRecallService


router = APIRouter(prefix="/chronic-recalls", tags=["chronic_recalls"])


@router.post(
    "",
    response_model=ChronicRecallResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_chronic_recall(
    payload: ChronicRecallCreateRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = ChronicRecallService(db)
    return service.create_recall(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        payload=payload,
    )
