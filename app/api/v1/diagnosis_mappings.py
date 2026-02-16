from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_db
from app.core.rbac import require_clinic_admin
from app.schemas.follow_up import (
    DiagnosisConditionMapCreateRequest,
    DiagnosisConditionMapResponse,
    DiagnosisConditionMapUpdateRequest,
)
from app.services.follow_up_service import FollowUpConfigurationService


router = APIRouter(prefix="/diagnosis-mappings", tags=["diagnosis_mappings"])


@router.get(
    "",
    response_model=list[DiagnosisConditionMapResponse],
    status_code=status.HTTP_200_OK,
)
def list_diagnosis_mappings(
    db=Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    service = FollowUpConfigurationService(db)
    return service.list_diagnosis_mappings(
        clinic_id=current_user.clinic_id,
        actor=current_user,
    )


@router.post(
    "",
    response_model=DiagnosisConditionMapResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_diagnosis_mapping(
    payload: DiagnosisConditionMapCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    service = FollowUpConfigurationService(db)
    return service.create_diagnosis_mapping(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        payload=payload,
    )


@router.patch(
    "/{mapping_id}/active",
    response_model=DiagnosisConditionMapResponse,
    status_code=status.HTTP_200_OK,
)
def set_diagnosis_mapping_active(
    mapping_id: UUID,
    payload: DiagnosisConditionMapUpdateRequest,
    db=Depends(get_db),
    current_user=Depends(require_clinic_admin),
):
    service = FollowUpConfigurationService(db)
    return service.set_mapping_active(
        clinic_id=current_user.clinic_id,
        mapping_id=mapping_id,
        actor=current_user,
        active=payload.active,
        justification=payload.justification,
    )
