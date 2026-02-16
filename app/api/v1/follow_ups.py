from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.auth import get_current_user
from app.core.dependencies import get_db
from app.schemas.follow_up import (
    ClinicianFollowUpDashboardResponse,
    FollowUpRescheduleRequest,
    FollowUpRescheduleResponse,
    ReceptionFollowUpDashboardResponse,
)
from app.services.follow_up_workflow_service import FollowUpWorkflowService
from app.shared.enums import PurposeOfUse


router = APIRouter(prefix="/follow-ups", tags=["follow_ups"])


@router.get(
    "/my",
    response_model=ClinicianFollowUpDashboardResponse,
)
def list_my_follow_ups(
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = FollowUpWorkflowService(db)
    data = service.list_clinician_follow_ups(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        purpose_of_use=purpose_of_use,
        justification=justification,
    )
    return ClinicianFollowUpDashboardResponse.model_validate(data)


@router.get(
    "/reception",
    response_model=ReceptionFollowUpDashboardResponse,
)
def list_reception_follow_ups(
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = FollowUpWorkflowService(db)
    data = service.list_reception_follow_ups(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        purpose_of_use=purpose_of_use,
        justification=justification,
    )
    return ReceptionFollowUpDashboardResponse.model_validate(data)


@router.post(
    "/{follow_up_id}/reschedule",
    response_model=FollowUpRescheduleResponse,
)
def reschedule_follow_up(
    follow_up_id: UUID,
    payload: FollowUpRescheduleRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = FollowUpWorkflowService(db)
    replacement = service.reschedule_follow_up(
        clinic_id=current_user.clinic_id,
        follow_up_id=follow_up_id,
        actor=current_user,
        due_at=payload.due_at,
        reason=payload.reason,
        justification=payload.justification,
    )
    replacement_payload = service.get_follow_up_item_by_id(
        clinic_id=current_user.clinic_id,
        follow_up_id=replacement.id,
    )
    return FollowUpRescheduleResponse(
        original_follow_up_id=follow_up_id,
        replacement=replacement_payload,
    )
