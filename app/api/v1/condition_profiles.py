from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_db
from app.core.rbac import require_clinic_admin
from app.schemas.follow_up import (
    ConditionProfileCreateRequest,
    ConditionProfileResponse,
    ConditionProfileUpdateRequest,
)
from app.services.follow_up_service import FollowUpConfigurationService


router = APIRouter(prefix="/condition-profiles", tags=["condition_profiles"])


@router.get(
    "",
    response_model=list[ConditionProfileResponse],
    status_code=status.HTTP_200_OK,
)
def list_condition_profiles(
    db=Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    service = FollowUpConfigurationService(db)
    return service.list_condition_profiles(
        clinic_id=current_user.clinic_id,
        actor=current_user,
    )


@router.post(
    "",
    response_model=ConditionProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_condition_profile(
    payload: ConditionProfileCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    service = FollowUpConfigurationService(db)
    return service.create_condition_profile(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        payload=payload,
    )


@router.patch(
    "/{profile_id}",
    response_model=ConditionProfileResponse,
    status_code=status.HTTP_200_OK,
)
def update_condition_profile(
    profile_id: UUID,
    payload: ConditionProfileUpdateRequest,
    db=Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    service = FollowUpConfigurationService(db)
    return service.update_condition_profile(
        clinic_id=current_user.clinic_id,
        profile_id=profile_id,
        actor=current_user,
        payload=payload,
    )
