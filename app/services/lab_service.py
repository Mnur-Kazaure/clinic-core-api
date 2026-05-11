# # app/services/lab_service.py
from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException, status

from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.models.lab_specimen import LabSpecimen
from app.models.visit import Visit
from app.schemas.lab import LabCompletionResponse, LabResultCreate
from app.shared.enums import (
    LabRequestStatus,
    LabRequestWorkflowStatus,
    LabResultLifecycleStatus,
    LabSpecimenStatus,
    RecordStatus,
    VisitStatus,
)
from app.services.event_service import EventService
from app.services.lab_role_access_service import LabRoleAccessService


QUALITATIVE_RESULT_KEYWORDS = (
    "hiv",
    "hepatitis b",
    "hepatitis c",
    "hbsag",
    "hcv",
    "vdrl",
    "pregnancy",
    "mrdt",
    "widal",
    "h. pylori",
    "h pylori",
    "blood grouping",
    "sickling",
    "urinalysis",
    "urine microscopy",
    "stool microscopy",
    "sputum afb",
)


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _is_qualitative_test(test_name: str) -> bool:
    normalized = test_name.strip().lower()
    return any(keyword in normalized for keyword in QUALITATIVE_RESULT_KEYWORDS)


class LabService:
    def __init__(self, db):
        self.db = db
        self.event_service = EventService(db)
        self.role_access = LabRoleAccessService(db)

    # ───────────────────────────────────────
    # RECORD LAB RESULT
    # ───────────────────────────────────────
    def record_result(
        self,
        lab_request_id: UUID,
        payload: LabResultCreate,
        *,
        technician_id: UUID,
    ) -> LabResult:
        actor = self.role_access.get_actor(actor_id=technician_id)
        self.role_access.assert_can_enter_result(actor=actor)
        lab_request = (
            self.db.query(LabRequest)
            .filter(LabRequest.id == lab_request_id)
            .first()
        )

        if not lab_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lab request not found",
            )

        if lab_request.status == LabRequestStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot record result for completed lab request",
            )

        result_value = _normalize_text(payload.result_value)
        result_unit = _normalize_text(payload.result_unit)
        reference_range = _normalize_text(payload.reference_range)
        if result_value is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Result value is required",
            )

        if not _is_qualitative_test(lab_request.test_name):
            if result_unit is None or reference_range is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=(
                        "Unit and reference range are required for quantitative tests"
                    ),
                )

        visit = (
            self.db.query(Visit)
            .filter(Visit.id == lab_request.visit_id)
            .first()
        )
        ready_specimen_exists = (
            self.db.query(LabSpecimen.id)
            .filter(
                LabSpecimen.request_item_id == lab_request.id,
                LabSpecimen.status.in_((LabSpecimenStatus.RECEIVED, LabSpecimenStatus.IN_PROCESS)),
            )
            .first()
        )
        if ready_specimen_exists is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Result entry requires a received specimen",
            )

        result = LabResult(
            lab_request_id=lab_request.id,
            request_item_id=lab_request.id,
            clinic_id=visit.clinic_id if visit else lab_request.clinic_id,
            technician_id=technician_id,
            status=LabResultLifecycleStatus.SUBMITTED,
            entered_by=technician_id,
            entered_at=datetime.now(timezone.utc),
            result_value=result_value,
            result_unit=result_unit,
            reference_range=reference_range,
            created_at=datetime.now(timezone.utc),
            record_status=RecordStatus.DRAFT,
        )

        lab_request.workflow_status = LabRequestWorkflowStatus.RESULT_ENTERED
        self.db.add(lab_request)
        self.db.add(result)
        self.event_service.build_event(
            event_type="LAB_RESULT_ENTERED",
            actor_id=technician_id,
            actor_role=actor.role.value,
            clinic_id=visit.clinic_id if visit else lab_request.clinic_id,
            patient_id=visit.patient_id if visit else None,
            emitter="lab",
            payload={
                "user_id": str(actor.user.id),
                "role": actor.role.value,
                "action_type": "LAB_RESULT_ENTERED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "unit_id": str(lab_request.target_unit_id) if lab_request.target_unit_id else None,
                "request_item_id": str(lab_request.id),
                "result_id": str(result.id),
                "metadata_json": {"mode": "legacy"},
            },
        )
        self.event_service.build_event(
            event_type="LAB_RESULT_SUBMITTED",
            actor_id=technician_id,
            actor_role=actor.role.value,
            clinic_id=visit.clinic_id if visit else lab_request.clinic_id,
            patient_id=visit.patient_id if visit else None,
            emitter="lab",
            payload={
                "user_id": str(actor.user.id),
                "role": actor.role.value,
                "action_type": "LAB_RESULT_SUBMITTED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "unit_id": str(lab_request.target_unit_id) if lab_request.target_unit_id else None,
                "request_item_id": str(lab_request.id),
                "result_id": str(result.id),
                "metadata_json": {"mode": "legacy"},
            },
        )
        self.event_service.build_event(
            event_type="LAB_RESULT_POSTED",
            actor_id=technician_id,
            actor_role=actor.role.value,
            clinic_id=visit.clinic_id if visit else lab_request.clinic_id,
            patient_id=visit.patient_id if visit else None,
            emitter="lab",
            payload={
                "lab_request_id": str(lab_request.id),
                "lab_result_id": str(result.id),
                "visit_id": str(lab_request.visit_id),
                "mode": "legacy",
                "status": result.status.value,
            },
        )
        self.db.commit()
        self.db.refresh(result)

        return result

    # ───────────────────────────────────────
    # COMPLETE LAB REQUEST (AUTHORITATIVE)
    # ───────────────────────────────────────
    def complete_lab_request(self, lab_request_id: UUID) -> LabRequest:
        """
        Explicit lab completion.

        - Idempotent
        - No Visit mutation
        - No Consultation mutation
        - Signals readiness only
        """

        lab_request = (
            self.db.query(LabRequest)
            .filter(LabRequest.id == lab_request_id)
            .first()
        )

        if not lab_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lab request not found",
            )

        if lab_request.status == LabRequestStatus.COMPLETED:
            return lab_request  # ✅ Idempotent

        has_result = (
            self.db.query(LabResult.id)
            .filter(LabResult.lab_request_id == lab_request.id)
            .filter(LabResult.status == LabResultLifecycleStatus.RELEASED)
            .first()
        )
        if not has_result:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot complete lab request without a released result",
            )

        lab_request.status = LabRequestStatus.COMPLETED
        lab_request.workflow_status = LabRequestWorkflowStatus.COMPLETED
        lab_request.completed_at = datetime.now(timezone.utc)

        self.db.add(lab_request)
        self.db.commit()
        self.db.refresh(lab_request)

        return lab_request

    def build_completion_response(self, *, lab_request: LabRequest) -> LabCompletionResponse:
        visit = self.db.query(Visit).filter(Visit.id == lab_request.visit_id).first()
        visit_ready_for_transition = bool(
            visit is not None and visit.status == VisitStatus.LAB_REQUESTED
        )
        return LabCompletionResponse(
            lab_request_id=lab_request.id,
            visit_id=lab_request.visit_id,
            status=lab_request.status,
            completed_at=lab_request.completed_at,
            visit_status=visit.status if visit is not None else None,
            visit_ready_for_transition=visit_ready_for_transition,
            suggested_next_visit_status=(
                VisitStatus.LAB_COMPLETED if visit_ready_for_transition else None
            ),
            visit_transition_expected_version=(
                visit.version if visit_ready_for_transition else None
            ),
        )
