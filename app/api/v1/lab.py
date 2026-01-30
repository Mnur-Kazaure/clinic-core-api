# # app/api/v1/lab.py

from fastapi import APIRouter, Depends, status, Query
from uuid import UUID

from app.core.dependencies import get_db
from app.core.guards.lab_guards import (
    require_lab_request_access_for_complete,
    require_lab_request_access_for_result,
    require_lab_request_access_for_read,
    require_lab_user,
)
from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.models.visit import Visit
from app.schemas.lab import LabResultCreate, LabResultResponse
from app.schemas.lab_request import LabRequestResponse
from app.services.lab_service import LabService
from app.shared.enums import LabRequestStatus
from app.services.access_log_service import AccessLogService

router = APIRouter(prefix="/lab", tags=["Lab"])


@router.get(
    "/requests",
    response_model=list[LabRequestResponse],
    status_code=status.HTTP_200_OK,
)
def list_lab_requests(
    status: LabRequestStatus | None = None,
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
):
    q = (
        db.query(LabRequest)
        .join(Visit, LabRequest.visit_id == Visit.id)
        .filter(Visit.clinic_id == current_user.clinic_id)
    )

    if status is not None:
        q = q.filter(LabRequest.status == status)

    return q.order_by(LabRequest.created_at.desc()).all()


@router.get(
    "/requests/{lab_request_id}/results",
    response_model=list[LabResultResponse],
    status_code=status.HTTP_200_OK,
)
def list_lab_results(
    lab_request_id: UUID,
    purpose_of_use: str = Query(..., min_length=2),
    reason: str = Query(..., min_length=2),
    break_glass: bool = Query(False),
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    lab_request=Depends(require_lab_request_access_for_read),
):
    visit = (
        db.query(Visit)
        .filter(Visit.id == lab_request.visit_id)
        .first()
    )
    if visit:
        if break_glass:
            AccessLogService(db).log_break_glass(
                actor=current_user,
                clinic_id=current_user.clinic_id,
                patient_id=visit.patient_id,
                purpose_of_use=purpose_of_use,
                reason=reason,
            )
        else:
            AccessLogService(db).log_chart_read(
                actor=current_user,
                clinic_id=current_user.clinic_id,
                patient_id=visit.patient_id,
                purpose_of_use=purpose_of_use,
                reason=reason,
            )
    return (
        db.query(LabResult)
        .filter(LabResult.lab_request_id == lab_request.id)
        .order_by(LabResult.created_at.asc())
        .all()
    )


# ───────────────────────────────────────
# SUBMIT LAB RESULT
# ───────────────────────────────────────
@router.post(
    "/requests/{lab_request_id}/results",
    response_model=LabResultResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_lab_result(
    lab_request_id: UUID,
    payload: LabResultCreate,
    db=Depends(get_db),
    lab_request=Depends(require_lab_request_access_for_result),
):
    service = LabService(db)
    return service.record_result(lab_request.id, payload)


# ───────────────────────────────────────
# COMPLETE LAB REQUEST (AUTHORITATIVE)
# ───────────────────────────────────────
@router.post(
    "/requests/{lab_request_id}/complete",
    status_code=status.HTTP_200_OK,
)
def complete_lab_request(
    lab_request_id: UUID,
    db=Depends(get_db),
    lab_request=Depends(require_lab_request_access_for_complete),
):
    service = LabService(db)
    lab_request = service.complete_lab_request(lab_request.id)

    return {
        "lab_request_id": lab_request.id,
        "status": lab_request.status,
        "completed_at": lab_request.completed_at,
        "visit_ready_for_transition": True,
        "suggested_next_visit_status": "LAB_COMPLETED",
    }
