# app/api/v1/doctor_lab.py
from fastapi import APIRouter, Depends, status, Query
from uuid import UUID

from app.core.dependencies import get_db
from app.core.auth import get_current_user
from app.core.guards.doctor_lab_guards import (
    require_doctor_lab_request_access,
    require_doctor_lab_requests_by_visit,
)
from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.models.visit import Visit
from app.schemas.lab_request import LabRequestResponse
from app.schemas.lab import LabResultResponse
from app.services.access_log_service import AccessLogService
from app.shared.enums import PurposeOfUse


router = APIRouter(prefix="/doctor", tags=["Doctor"])


@router.get(
    "/visits/{visit_id}/lab-requests",
    response_model=list[LabRequestResponse],
    status_code=status.HTTP_200_OK,
)
def list_lab_requests_for_visit(
    visit_id: UUID,
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
    break_glass: bool = Query(False),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    visit=Depends(require_doctor_lab_requests_by_visit),
):
    if break_glass:
        AccessLogService(db).log_break_glass(
            actor=current_user,
            clinic_id=current_user.clinic_id,
            patient_id=visit.patient_id,
            purpose_of_use=purpose_of_use,
            justification=justification,
            resource="LAB_REQUESTS",
        )
    else:
        AccessLogService(db).log_chart_read(
            actor=current_user,
            clinic_id=current_user.clinic_id,
            patient_id=visit.patient_id,
            purpose_of_use=purpose_of_use,
            justification=justification,
            resource="LAB_REQUESTS",
        )
    return (
        db.query(LabRequest)
        .filter(LabRequest.visit_id == visit_id)
        .order_by(LabRequest.created_at.desc())
        .all()
    )


@router.get(
    "/lab-requests/{lab_request_id}/results",
    response_model=list[LabResultResponse],
    status_code=status.HTTP_200_OK,
)
def list_lab_results_for_request(
    lab_request_id: UUID,
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
    break_glass: bool = Query(False),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    lab_request=Depends(require_doctor_lab_request_access),
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
