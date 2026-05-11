# # app/api/v1/lab.py

import asyncio
from json import dumps

from fastapi import APIRouter, Depends, status, Query, Request
from fastapi.responses import StreamingResponse
from uuid import UUID

from app.core.database import SessionLocal
from app.core.dependencies import get_db
from app.core.guards.lab_guards import (
    require_lab_manager_user,
    require_lab_request_access_for_complete,
    require_lab_request_access_for_result,
    require_lab_request_access_for_read,
    require_lab_result_access,
    require_lab_selected_unit,
    require_lab_specimen_access,
    require_lab_user,
)
from app.models.lab_request import LabRequest
from app.models.billing_item import BillingItem
from app.models.lab_result import LabResult
from app.models.service_line import ServiceLine
from app.models.patient import Patient
from app.models.patient_mrn import PatientMRN
from app.models.patient_identity_map import PatientIdentityMap
from app.models.identity_map_revocation import IdentityMapRevocation
from app.models.user import User
from app.models.visit import Visit
from app.schemas.lab_foundation import (
    LabResultTemplateResponse,
    LabSpecimenCreate,
    LabSpecimenEventCreate,
    LabSpecimenEventResponse,
    LabSpecimenResponse,
)
from app.schemas.lab import LabCompletionResponse, LabResultCreate, LabResultResponse
from app.schemas.lab_workflow import LabRequestWorkflowStateResponse
from app.schemas.lab_safety import (
    LabCriticalAlertResponse,
    LabQcResultCreate,
    LabQcResultResponse,
    LabQcRunCreate,
    LabQcRunResponse,
    LabResultAmendCreate,
    LabResultActionResponse,
    LabResultReleaseRequest,
    StructuredLabResultCreate,
    StructuredLabResultResponse,
)
from app.schemas.lab_request import LabRequestResponse
from app.schemas.lab_manager import (
    LabManagerBadgeSnapshotResponse,
    LabManagerConfigurationRequestCreate,
    LabManagerConfigurationRequestResponse,
    LabManagerDashboardResponse,
    LabManagerStaffAssignmentUpdateRequest,
    LabManagerStaffSummaryResponse,
)
from app.schemas.lab_workspace import (
    LabWorkspaceBenchSnapshotResponse,
    LabManagerOverviewResponse,
    LabWorkspaceOverviewResponse,
    LabWorkspaceQcRunSummaryResponse,
    LabWorkspaceSpecimenSummaryResponse,
)
from app.api.v1.lab_query_parsing import parse_optional_iso_date
from app.services.lab_foundation_service import LabFoundationService
from app.services.lab_manager_badge_service import LabManagerBadgeService
from app.services.lab_manager_governance_service import LabManagerGovernanceService
from app.services.lab_request_workflow_service import LabRequestWorkflowService
from app.services.lab_safety_service import LabSafetyService
from app.services.lab_service import LabService
from app.services.lab_workspace_service import LabWorkspaceService
from app.services.lab_workspace_attention_service import LabWorkspaceAttentionService
from app.services.billing_workflow_service import BillingWorkflowService
from app.shared.enums import (
    BillingItemStatus,
    GovernanceSectionKey,
    LabRequestStatus,
    LabRequestWorkflowStatus,
    LabSpecimenStatus,
    PurposeOfUse,
    MRNStatus,
)
from app.services.access_log_service import AccessLogService

router = APIRouter(prefix="/lab", tags=["Lab"])


def _encode_sse_event(*, event: str, data: dict, event_id: str | None = None) -> str:
    lines: list[str] = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {dumps(data)}")
    return "\n".join(lines) + "\n\n"


def _serialize_structured_result(result) -> dict:
    verification_policy = getattr(result, "_verification_policy", "OPTIONAL")
    values = getattr(result, "_value_rows", [])
    return {
        "id": result.id,
        "request_item_id": result.request_item_id,
        "template_id": result.template_id,
        "template_version": result.template_version,
        "status": result.status,
        "amendment_reason": result.amendment_reason,
        "entered_by": result.entered_by,
        "entered_at": result.entered_at,
        "verified_by": result.verified_by,
        "verified_at": result.verified_at,
        "released_by": result.released_by,
        "released_at": result.released_at,
        "verification_policy": verification_policy,
        "values": [
            {
                "id": value.id,
                "template_field_id": value.template_field_id,
                "value_string": value.value_string,
                "value_number": value.value_number,
                "value_boolean": value.value_boolean,
                "value_json": value.value_json,
                "abnormal_flag": value.abnormal_flag,
                "critical_flag": value.critical_flag,
            }
            for value in values
        ],
    }


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
    workflow_status: LabRequestWorkflowStatus | None = None,
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    selected_unit: ServiceLine = Depends(require_lab_selected_unit),
):
    return LabWorkspaceService(db).list_unit_requests(
        clinic_id=current_user.clinic_id,
        unit_id=selected_unit.id,
        status=status,
        workflow_status=workflow_status,
    )


@router.get(
    "/workspace/overview",
    response_model=LabWorkspaceOverviewResponse,
    status_code=status.HTTP_200_OK,
)
def get_lab_workspace_overview(
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    selected_unit: ServiceLine = Depends(require_lab_selected_unit),
):
    return LabWorkspaceService(db).get_unit_overview(
        clinic_id=current_user.clinic_id,
        unit=selected_unit,
    )


@router.get(
    "/workspace/specimens",
    response_model=list[LabWorkspaceSpecimenSummaryResponse],
    status_code=status.HTTP_200_OK,
)
def list_lab_workspace_specimens(
    status: LabSpecimenStatus | None = None,
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    selected_unit: ServiceLine = Depends(require_lab_selected_unit),
):
    return LabWorkspaceService(db).list_unit_specimens(
        clinic_id=current_user.clinic_id,
        unit_id=selected_unit.id,
        status=status,
    )


@router.get(
    "/workspace/qc-runs",
    response_model=list[LabWorkspaceQcRunSummaryResponse],
    status_code=status.HTTP_200_OK,
)
def list_lab_workspace_qc_runs(
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    selected_unit: ServiceLine = Depends(require_lab_selected_unit),
):
    return LabWorkspaceService(db).list_unit_qc_runs(
        clinic_id=current_user.clinic_id,
        unit_id=selected_unit.id,
    )


@router.get(
    "/workspace/bench",
    response_model=LabWorkspaceBenchSnapshotResponse,
    status_code=status.HTTP_200_OK,
)
def get_lab_workspace_bench_snapshot(
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    selected_unit: ServiceLine = Depends(require_lab_selected_unit),
):
    return LabWorkspaceAttentionService(db).get_snapshot(
        clinic_id=current_user.clinic_id,
        unit=selected_unit,
    )


@router.get(
    "/workspace/bench-stream",
    status_code=status.HTTP_200_OK,
)
async def stream_lab_workspace_bench_snapshot(
    request: Request,
    current_user=Depends(require_lab_user),
    selected_unit: ServiceLine = Depends(require_lab_selected_unit),
):
    async def event_stream():
        last_signature: str | None = None
        heartbeat_interval_seconds = 15
        poll_interval_seconds = 3
        last_keepalive_at = asyncio.get_running_loop().time()

        while True:
            if await request.is_disconnected():
                break

            with SessionLocal() as stream_db:
                attention_service = LabWorkspaceAttentionService(stream_db)
                snapshot = attention_service.get_snapshot(
                    clinic_id=current_user.clinic_id,
                    unit=selected_unit,
                )
                signature = attention_service.snapshot_signature(snapshot)

            if signature != last_signature:
                yield _encode_sse_event(
                    event="bench_snapshot",
                    data=snapshot.model_dump(mode="json"),
                    event_id=snapshot.generated_at.isoformat(),
                )
                last_signature = signature
                last_keepalive_at = asyncio.get_running_loop().time()
            elif asyncio.get_running_loop().time() - last_keepalive_at >= heartbeat_interval_seconds:
                yield ": keepalive\n\n"
                last_keepalive_at = asyncio.get_running_loop().time()

            await asyncio.sleep(poll_interval_seconds)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/manager/overview",
    response_model=LabManagerOverviewResponse,
    status_code=status.HTTP_200_OK,
)
def get_lab_manager_overview(
    db=Depends(get_db),
    current_user=Depends(require_lab_manager_user),
):
    return LabWorkspaceService(db).get_manager_overview(
        clinic_id=current_user.clinic_id,
    )


@router.get(
    "/manager/badges",
    response_model=LabManagerBadgeSnapshotResponse,
    status_code=status.HTTP_200_OK,
)
def get_lab_manager_badges(
    db=Depends(get_db),
    current_user=Depends(require_lab_manager_user),
):
    return LabManagerBadgeService(db).get_snapshot(
        clinic_id=current_user.clinic_id,
        user_id=current_user.id,
    )


@router.post(
    "/manager/badges/{section_key}/viewed",
    response_model=LabManagerBadgeSnapshotResponse,
    status_code=status.HTTP_200_OK,
)
def mark_lab_manager_badge_viewed(
    section_key: GovernanceSectionKey,
    db=Depends(get_db),
    current_user=Depends(require_lab_manager_user),
):
    return LabManagerBadgeService(db).mark_section_viewed(
        clinic_id=current_user.clinic_id,
        user_id=current_user.id,
        section_key=section_key,
    )


@router.get(
    "/manager/badge-stream",
    status_code=status.HTTP_200_OK,
)
async def stream_lab_manager_badges(
    request: Request,
    current_user=Depends(require_lab_manager_user),
):
    async def event_stream():
        last_signature: str | None = None
        heartbeat_interval_seconds = 15
        poll_interval_seconds = 3
        last_keepalive_at = asyncio.get_running_loop().time()

        while True:
            if await request.is_disconnected():
                break

            with SessionLocal() as stream_db:
                badge_service = LabManagerBadgeService(stream_db)
                snapshot = badge_service.get_snapshot(
                    clinic_id=current_user.clinic_id,
                    user_id=current_user.id,
                )
                signature = badge_service.snapshot_signature(snapshot)

            if signature != last_signature:
                yield _encode_sse_event(
                    event="badge_snapshot",
                    data=snapshot.model_dump(mode="json"),
                    event_id=snapshot.generated_at.isoformat(),
                )
                last_signature = signature
                last_keepalive_at = asyncio.get_running_loop().time()
            elif asyncio.get_running_loop().time() - last_keepalive_at >= heartbeat_interval_seconds:
                yield ": keepalive\n\n"
                last_keepalive_at = asyncio.get_running_loop().time()

            await asyncio.sleep(poll_interval_seconds)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/manager/dashboard",
    response_model=LabManagerDashboardResponse,
    status_code=status.HTTP_200_OK,
)
def get_lab_manager_dashboard(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_lab_manager_user),
):
    resolved_start = parse_optional_iso_date(start_date, field_name="start_date")
    resolved_end = parse_optional_iso_date(end_date, field_name="end_date")
    return LabManagerGovernanceService(db).get_dashboard(
        clinic_id=current_user.clinic_id,
        start_date=resolved_start,
        end_date=resolved_end,
    )


@router.patch(
    "/manager/staff/{staff_id}/assignment",
    response_model=LabManagerStaffSummaryResponse,
    status_code=status.HTTP_200_OK,
)
def update_lab_manager_staff_assignment(
    staff_id: UUID,
    payload: LabManagerStaffAssignmentUpdateRequest,
    db=Depends(get_db),
    current_user=Depends(require_lab_manager_user),
):
    return LabManagerGovernanceService(db).update_staff_assignment(
        clinic_id=current_user.clinic_id,
        actor_id=current_user.id,
        staff_id=staff_id,
        payload=payload,
    )


@router.post(
    "/manager/configuration-requests",
    response_model=LabManagerConfigurationRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_lab_manager_configuration_request(
    payload: LabManagerConfigurationRequestCreate,
    db=Depends(get_db),
    current_user=Depends(require_lab_manager_user),
):
    return LabManagerGovernanceService(db).create_configuration_request(
        clinic_id=current_user.clinic_id,
        actor_id=current_user.id,
        payload=payload,
    )


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


@router.get(
    "/requests/{lab_request_id}/workflow-state",
    response_model=LabRequestWorkflowStateResponse,
    status_code=status.HTTP_200_OK,
)
def get_lab_request_workflow_state(
    lab_request_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    lab_request=Depends(require_lab_request_access_for_read),
):
    return LabRequestWorkflowService(db).get_workflow_state(lab_request=lab_request)


@router.get(
    "/requests/{lab_request_id}/template",
    response_model=LabResultTemplateResponse,
    status_code=status.HTTP_200_OK,
)
def get_lab_request_template(
    lab_request_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    lab_request=Depends(require_lab_request_access_for_read),
):
    return LabFoundationService(db).get_request_template(lab_request=lab_request)


@router.get(
    "/requests/{lab_request_id}/specimens",
    response_model=list[LabSpecimenResponse],
    status_code=status.HTTP_200_OK,
)
def list_lab_specimens(
    lab_request_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    lab_request=Depends(require_lab_request_access_for_read),
):
    return LabFoundationService(db).list_specimens_for_request(lab_request_id=lab_request.id)


@router.post(
    "/requests/{lab_request_id}/specimens",
    response_model=LabSpecimenResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_lab_specimen(
    lab_request_id: UUID,
    payload: LabSpecimenCreate,
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    lab_request=Depends(require_lab_request_access_for_result),
):
    return LabFoundationService(db).create_specimen(
        lab_request=lab_request,
        actor_id=current_user.id,
        payload=payload,
    )


@router.post(
    "/specimens/{specimen_id}/events",
    response_model=LabSpecimenEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_lab_specimen_event(
    specimen_id: UUID,
    payload: LabSpecimenEventCreate,
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    specimen=Depends(require_lab_specimen_access),
):
    return LabFoundationService(db).record_specimen_event(
        specimen_id=specimen.id,
        clinic_id=current_user.clinic_id,
        actor_id=current_user.id,
        payload=payload,
    )


# ───────────────────────────────────────
# SUBMIT LAB RESULT
# ───────────────────────────────────────
@router.post(
    "/requests/{lab_request_id}/structured-results",
    response_model=StructuredLabResultResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_structured_lab_result(
    lab_request_id: UUID,
    payload: StructuredLabResultCreate,
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    lab_request=Depends(require_lab_request_access_for_result),
):
    result = LabSafetyService(db).submit_structured_result(
        lab_request=lab_request,
        actor_id=current_user.id,
        payload=payload,
    )
    return _serialize_structured_result(result)


@router.post(
    "/results/{result_id}/verify",
    response_model=LabResultActionResponse,
    status_code=status.HTTP_200_OK,
)
def verify_lab_result(
    result_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    result=Depends(require_lab_result_access),
):
    result = LabSafetyService(db).verify_result(
        result_id=result.id,
        clinic_id=current_user.clinic_id,
        actor_id=current_user.id,
    )
    return {
        "result_id": result.id,
        "status": result.status,
        "verification_policy": getattr(result, "_verification_policy", "OPTIONAL"),
        "critical_alert_count": getattr(result, "_critical_alert_count", 0),
    }


@router.post(
    "/results/{result_id}/release",
    response_model=LabResultActionResponse,
    status_code=status.HTTP_200_OK,
)
def release_lab_result(
    result_id: UUID,
    payload: LabResultReleaseRequest | None = None,
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    result=Depends(require_lab_result_access),
):
    result = LabSafetyService(db).release_result(
        result_id=result.id,
        clinic_id=current_user.clinic_id,
        actor_id=current_user.id,
        payload=payload,
    )
    return {
        "result_id": result.id,
        "status": result.status,
        "verification_policy": getattr(result, "_verification_policy", "OPTIONAL"),
        "critical_alert_count": getattr(result, "_critical_alert_count", 0),
    }


@router.post(
    "/results/{result_id}/amend",
    response_model=StructuredLabResultResponse,
    status_code=status.HTTP_200_OK,
)
def amend_lab_result(
    result_id: UUID,
    payload: LabResultAmendCreate,
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    result=Depends(require_lab_result_access),
):
    amended = LabSafetyService(db).amend_result(
        result_id=result.id,
        clinic_id=current_user.clinic_id,
        actor_id=current_user.id,
        payload=payload,
    )
    return _serialize_structured_result(amended)


@router.get(
    "/results/{result_id}/alerts",
    response_model=list[LabCriticalAlertResponse],
    status_code=status.HTTP_200_OK,
)
def list_lab_result_alerts(
    result_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    result=Depends(require_lab_result_access),
):
    return LabSafetyService(db).list_result_alerts(
        result_id=result.id,
        clinic_id=current_user.clinic_id,
    )


@router.post(
    "/qc/runs",
    response_model=LabQcRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_lab_qc_run(
    payload: LabQcRunCreate,
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    selected_unit: ServiceLine = Depends(require_lab_selected_unit),
):
    return LabSafetyService(db).create_qc_run(
        clinic_id=current_user.clinic_id,
        actor_id=current_user.id,
        payload=payload,
        expected_unit_id=selected_unit.id,
    )


@router.post(
    "/qc/runs/{qc_run_id}/results",
    response_model=LabQcResultResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_lab_qc_result(
    qc_run_id: UUID,
    payload: LabQcResultCreate,
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    selected_unit: ServiceLine = Depends(require_lab_selected_unit),
):
    return LabSafetyService(db).record_qc_result(
        qc_run_id=qc_run_id,
        clinic_id=current_user.clinic_id,
        actor_id=current_user.id,
        payload=payload,
        expected_unit_id=selected_unit.id,
    )


@router.post(
    "/requests/{lab_request_id}/results",
    response_model=LabResultResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_lab_result(
    lab_request_id: UUID,
    payload: LabResultCreate,
    db=Depends(get_db),
    current_user=Depends(require_lab_user),
    lab_request=Depends(require_lab_request_access_for_result),
):
    service = LabService(db)
    return service.record_result(
        lab_request.id,
        payload,
        technician_id=current_user.id,
    )


# ───────────────────────────────────────
# COMPLETE LAB REQUEST (AUTHORITATIVE)
# ───────────────────────────────────────
@router.post(
    "/requests/{lab_request_id}/complete",
    response_model=LabCompletionResponse,
    status_code=status.HTTP_200_OK,
)
def complete_lab_request(
    lab_request_id: UUID,
    db=Depends(get_db),
    lab_request=Depends(require_lab_request_access_for_complete),
):
    service = LabService(db)
    lab_request = service.complete_lab_request(lab_request.id)
    return service.build_completion_response(lab_request=lab_request)
