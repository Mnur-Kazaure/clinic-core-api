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
from app.models.patient import Patient
from app.models.patient_mrn import PatientMRN
from app.models.patient_identity_map import PatientIdentityMap
from app.models.identity_map_revocation import IdentityMapRevocation
from app.models.user import User
from app.models.visit import Visit
from app.schemas.lab import LabResultCreate, LabResultResponse
from app.schemas.lab_request import LabRequestResponse
from app.services.lab_service import LabService
from app.shared.enums import LabRequestStatus, PurposeOfUse, MRNStatus
from app.services.access_log_service import AccessLogService

router = APIRouter(prefix="/lab", tags=["Lab"])


def _resolve_canonical_patient_id(db, *, clinic_id: UUID, patient_id: UUID) -> UUID:
    visited = set()
    current = patient_id
    for _ in range(10):
        if current in visited:
            return patient_id
        visited.add(current)
        mapping = (
            db.query(PatientIdentityMap)
            .filter(
                PatientIdentityMap.clinic_id == clinic_id,
                PatientIdentityMap.from_patient_id == current,
            )
            .first()
        )
        if not mapping:
            return current
        revoked = (
            db.query(IdentityMapRevocation)
            .filter(
                IdentityMapRevocation.clinic_id == clinic_id,
                IdentityMapRevocation.map_id == mapping.id,
            )
            .first()
        )
        if revoked:
            return current
        current = mapping.to_patient_id
    return patient_id


def _attach_patient_info(db, *, clinic_id: UUID, lab_requests: list[LabRequest]) -> None:
    if not lab_requests:
        return
    visit_ids = {request.visit_id for request in lab_requests}
    visits = db.query(Visit).filter(Visit.id.in_(visit_ids)).all()
    visit_map = {visit.id: visit for visit in visits}
    patient_ids = {visit.patient_id for visit in visits}
    patients = db.query(Patient).filter(Patient.id.in_(patient_ids)).all()
    patient_map = {patient.id: patient.full_name for patient in patients}
    canonical_map = {
        patient_id: _resolve_canonical_patient_id(
            db, clinic_id=clinic_id, patient_id=patient_id
        )
        for patient_id in patient_ids
    }
    canonical_ids = set(canonical_map.values())
    mrns = (
        db.query(PatientMRN.patient_id, PatientMRN.mrn)
        .filter(
            PatientMRN.patient_id.in_(canonical_ids),
            PatientMRN.clinic_id == clinic_id,
            PatientMRN.status == MRNStatus.ACTIVE,
        )
        .all()
    )
    mrn_map = {patient_id: mrn for patient_id, mrn in mrns}
    requester_ids = {request.requested_by for request in lab_requests}
    users = db.query(User).filter(User.id.in_(requester_ids)).all()
    user_map = {user.id: user for user in users}

    for request in lab_requests:
        visit = visit_map.get(request.visit_id)
        if not visit:
            request.patient_id = None
            request.patient_name = None
            request.patient_mrn = None
            request.requested_by_name = None
            request.requested_by_role = None
            continue
        request.patient_id = visit.patient_id
        request.patient_name = patient_map.get(visit.patient_id)
        canonical_id = canonical_map.get(visit.patient_id, visit.patient_id)
        request.patient_mrn = mrn_map.get(canonical_id)
        requester = user_map.get(request.requested_by)
        request.requested_by_name = requester.full_name if requester else None
        request.requested_by_role = requester.role if requester else None


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

    lab_requests = q.order_by(LabRequest.created_at.desc()).all()
    _attach_patient_info(
        db,
        clinic_id=current_user.clinic_id,
        lab_requests=lab_requests,
    )
    return lab_requests


@router.get(
    "/requests/{lab_request_id}/results",
    response_model=list[LabResultResponse],
    status_code=status.HTTP_200_OK,
)
def list_lab_results(
    lab_request_id: UUID,
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
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
                justification=justification,
                resource="LAB_RESULT",
            )
        else:
            AccessLogService(db).log_chart_read(
                actor=current_user,
                clinic_id=current_user.clinic_id,
                patient_id=visit.patient_id,
                purpose_of_use=purpose_of_use,
                justification=justification,
                resource="LAB_RESULT",
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
