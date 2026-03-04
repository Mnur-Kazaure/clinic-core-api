# app/api/v1/admissions.py
from fastapi import APIRouter, Depends, status
from uuid import UUID

from app.core.dependencies import get_db
from app.core.auth import get_current_user
from app.core.guards.admission_guards import (
    require_admission_role,
    require_admission_access,
    require_admission_request_role,
    require_admission_decision_role,
)
from app.schemas.admission import (
    AdmissionCreateRequest,
    AdmissionCancelRequest,
    AdmissionBedReleaseRequest,
    AdmissionDischargeRequest,
    AdmissionResponse,
    AdmissionRequestCreateRequest,
    AdmissionRequestDecisionRequest,
    AdmissionRequestResponse,
)
from app.services.admission_service import AdmissionService
from app.services.admission_request_service import AdmissionRequestService
from app.shared.enums import AdmissionRequestStatus


router = APIRouter(prefix="/admissions", tags=["admissions"])


@router.post(
    "",
    response_model=AdmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_admission(
    payload: AdmissionCreateRequest,
    db=Depends(get_db),
    user=Depends(require_admission_role),
):
    service = AdmissionService(db)
    return service.create_admission(
        patient_id=payload.patient_id,
        admission_type=payload.admission_type,
        actor=user,
        break_glass=payload.break_glass,
        purpose_of_use=payload.purpose_of_use,
        reason=payload.reason,
    )


@router.post(
    "/requests",
    response_model=AdmissionRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_admission_request(
    payload: AdmissionRequestCreateRequest,
    db=Depends(get_db),
    user=Depends(require_admission_request_role),
):
    service = AdmissionRequestService(db)
    return service.create_request(
        patient_id=payload.patient_id,
        admission_type=payload.admission_type,
        reason=payload.reason,
        actor=user,
    )


@router.get(
    "/requests",
    response_model=list[AdmissionRequestResponse],
)
def list_admission_requests(
    status_filter: AdmissionRequestStatus | None = None,
    db=Depends(get_db),
    user=Depends(require_admission_request_role),
):
    service = AdmissionRequestService(db)
    return service.list_requests(actor=user, status=status_filter)


@router.post(
    "/requests/{request_id}/approve",
    response_model=AdmissionRequestResponse,
)
def approve_admission_request(
    request_id: UUID,
    payload: AdmissionRequestDecisionRequest,
    db=Depends(get_db),
    user=Depends(require_admission_decision_role),
):
    service = AdmissionRequestService(db)
    request, admission = service.approve_request(
        request_id=request_id,
        actor=user,
        decision_reason=payload.reason,
    )
    response = AdmissionRequestResponse.model_validate(request)
    response.admission_id = admission.id
    return response


@router.post(
    "/requests/{request_id}/reject",
    response_model=AdmissionRequestResponse,
)
def reject_admission_request(
    request_id: UUID,
    payload: AdmissionRequestDecisionRequest,
    db=Depends(get_db),
    user=Depends(require_admission_decision_role),
):
    service = AdmissionRequestService(db)
    return service.reject_request(
        request_id=request_id,
        actor=user,
        decision_reason=payload.reason,
    )


@router.post(
    "/requests/{request_id}/cancel",
    response_model=AdmissionRequestResponse,
)
def cancel_admission_request(
    request_id: UUID,
    payload: AdmissionRequestDecisionRequest,
    db=Depends(get_db),
    user=Depends(require_admission_request_role),
):
    service = AdmissionRequestService(db)
    return service.cancel_request(
        request_id=request_id,
        actor=user,
        reason=payload.reason,
    )


@router.get(
    "/{admission_id}",
    response_model=AdmissionResponse,
)
def get_admission(
    admission=Depends(require_admission_access),
):
    return admission


@router.post(
    "/{admission_id}/discharge",
    response_model=AdmissionResponse,
)
def discharge_admission(
    admission_id: UUID,
    payload: AdmissionDischargeRequest = AdmissionDischargeRequest(),
    db=Depends(get_db),
    user=Depends(require_admission_role),
):
    service = AdmissionService(db)
    return service.discharge_admission(
        admission_id=admission_id,
        actor=user,
        disposition=payload.disposition,
        transferred_to_facility=payload.transferred_to_facility,
        death_pronounced_at=payload.death_pronounced_at,
        discharge_notes=payload.discharge_notes,
    )


@router.post(
    "/{admission_id}/cancel",
    response_model=AdmissionResponse,
)
def cancel_admission(
    admission_id: UUID,
    payload: AdmissionCancelRequest,
    db=Depends(get_db),
    user=Depends(require_admission_role),
):
    service = AdmissionService(db)
    return service.cancel_admission(
        admission_id=admission_id,
        actor=user,
        reason=payload.reason,
    )


@router.post(
    "/{admission_id}/bed/release",
    response_model=AdmissionResponse,
)
def release_admission_bed(
    admission_id: UUID,
    payload: AdmissionBedReleaseRequest,
    db=Depends(get_db),
    user=Depends(require_admission_role),
):
    service = AdmissionService(db)
    return service.release_admission_bed(
        admission_id=admission_id,
        actor=user,
        reason=payload.reason,
    )
