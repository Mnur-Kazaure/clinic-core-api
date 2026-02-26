# # app/services/lab_service.py
from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException, status

from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.models.visit import Visit
from app.schemas.lab import LabResultCreate
from app.shared.enums import LabRequestStatus, RecordStatus
from app.services.event_service import EventService


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

    # ───────────────────────────────────────
    # RECORD LAB RESULT
    # ───────────────────────────────────────
    def record_result(self, lab_request_id: UUID, payload: LabResultCreate) -> LabResult:
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

        recorded_at = datetime.now(timezone.utc)

        result = LabResult(
            lab_request_id=lab_request.id,
            clinic_id=visit.clinic_id if visit else lab_request.clinic_id,
            technician_id=payload.technician_id,
            result_value=result_value,
            result_unit=result_unit,
            reference_range=reference_range,
            created_at=recorded_at,
            record_status=RecordStatus.SIGNED,
            signed_at=recorded_at,
        )

        self.db.add(result)
        # Lab result submission is treated as handoff-complete for this request.
        lab_request.status = LabRequestStatus.COMPLETED
        lab_request.completed_at = recorded_at
        self.db.add(lab_request)
        self.db.commit()
        self.db.refresh(result)

        self.event_service.emit(
            event_type="LAB_RESULT_POSTED",
            actor_id=payload.technician_id,
            actor_role="LAB",
            clinic_id=visit.clinic_id if visit else lab_request.clinic_id,
            patient_id=visit.patient_id if visit else None,
            emitter="lab",
            payload={
                "lab_request_id": str(lab_request.id),
                "lab_result_id": str(result.id),
                "visit_id": str(lab_request.visit_id),
            },
        )

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
            .first()
        )
        if not has_result:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot complete lab request without recorded results",
            )

        lab_request.status = LabRequestStatus.COMPLETED
        lab_request.completed_at = datetime.now(timezone.utc)

        self.db.add(lab_request)
        self.db.commit()
        self.db.refresh(lab_request)

        return lab_request
