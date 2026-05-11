# app/api/v1/doctor_lab.py
from fastapi import APIRouter, Depends, status, Query
from uuid import UUID

from app.core.dependencies import get_db
from app.core.auth import get_current_user
from app.core.guards.doctor_lab_guards import (
    require_doctor_lab_history_access,
    require_doctor_lab_request_access,
    require_doctor_lab_requests_by_visit,
)
from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.models.patient import Patient
from app.models.visit import Visit
from app.models.user import User
from app.schemas.doctor_lab_reporting import (
    DoctorLabResultDetailResponse,
    DoctorLabVisitResultSummaryResponse,
    DoctorPatientLabHistoryEntryResponse,
)
from app.schemas.lab_request import LabRequestResponse
from app.schemas.lab import LabResultResponse
from app.services.access_log_service import AccessLogService
from app.services.billing_workflow_service import BillingWorkflowService
from app.services.doctor_lab_reporting_service import DoctorLabReportingService
from app.shared.enums import PurposeOfUse


router = APIRouter(prefix="/doctor", tags=["Doctor"])


def _attach_requester_info(db, lab_requests: list[LabRequest]) -> None:
    if not lab_requests:
        return
    requester_ids = {request.requested_by for request in lab_requests}
    users = db.query(User).filter(User.id.in_(requester_ids)).all()
    user_map = {user.id: user for user in users}
    for request in lab_requests:
        requester = user_map.get(request.requested_by)
        request.requested_by_name = requester.full_name if requester else None
        request.requested_by_role = requester.role if requester else None


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
    lab_requests = (
        db.query(LabRequest)
        .filter(LabRequest.visit_id == visit_id)
        .order_by(LabRequest.created_at.desc())
        .all()
    )
    _attach_requester_info(db, lab_requests)
    BillingWorkflowService(db).attach_lab_request_billing(lab_requests=lab_requests)
    return lab_requests


@router.get(
    "/visits/{visit_id}/lab-results",
    response_model=list[DoctorLabVisitResultSummaryResponse],
    status_code=status.HTTP_200_OK,
)
def list_released_lab_results_for_visit(
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
            resource="LAB_RESULT_VISIT_SUMMARY",
        )
    else:
        AccessLogService(db).log_chart_read(
            actor=current_user,
            clinic_id=current_user.clinic_id,
            patient_id=visit.patient_id,
            purpose_of_use=purpose_of_use,
            justification=justification,
            resource="LAB_RESULT_VISIT_SUMMARY",
        )

    return DoctorLabReportingService(db).list_visit_results(visit=visit)


@router.get(
    "/visits/{visit_id}/lab-results/{result_id}",
    response_model=DoctorLabResultDetailResponse,
    status_code=status.HTTP_200_OK,
)
def get_released_lab_result_detail(
    visit_id: UUID,
    result_id: UUID,
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
            resource="LAB_RESULT_VISIT_DETAIL",
            extra_payload={"result_id": str(result_id)},
        )
    else:
        AccessLogService(db).log_chart_read(
            actor=current_user,
            clinic_id=current_user.clinic_id,
            patient_id=visit.patient_id,
            purpose_of_use=purpose_of_use,
            justification=justification,
            resource="LAB_RESULT_VISIT_DETAIL",
            extra_payload={"result_id": str(result_id)},
        )

    return DoctorLabReportingService(db).get_visit_result_detail(
        visit=visit,
        result_id=result_id,
    )


@router.get(
    "/patients/{patient_id}/lab-history/{test_code}",
    response_model=list[DoctorPatientLabHistoryEntryResponse],
    status_code=status.HTTP_200_OK,
)
def list_patient_lab_history(
    patient_id: UUID,
    test_code: str,
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
    break_glass: bool = Query(False),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    patient: Patient = Depends(require_doctor_lab_history_access),
):
    if break_glass:
        AccessLogService(db).log_break_glass(
            actor=current_user,
            clinic_id=current_user.clinic_id,
            patient_id=patient.id,
            purpose_of_use=purpose_of_use,
            justification=justification,
            resource="LAB_RESULT_PATIENT_HISTORY",
            extra_payload={"test_code": test_code},
        )
    else:
        AccessLogService(db).log_chart_read(
            actor=current_user,
            clinic_id=current_user.clinic_id,
            patient_id=patient.id,
            purpose_of_use=purpose_of_use,
            justification=justification,
            resource="LAB_RESULT_PATIENT_HISTORY",
            extra_payload={"test_code": test_code},
        )

    return DoctorLabReportingService(db).list_patient_history(
        patient_id=patient.id,
        clinic_id=current_user.clinic_id,
        test_identifier=test_code,
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
