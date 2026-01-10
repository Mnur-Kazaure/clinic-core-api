# # app/services/lab_service.py
from datetime import datetime
from uuid import UUID
from fastapi import HTTPException, status

from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.schemas.lab import LabResultCreate
from app.shared.enums import LabRequestStatus


class LabService:
    def __init__(self, db):
        self.db = db

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

        result = LabResult(
            lab_request_id=lab_request.id,
            technician_id=payload.technician_id,
            result_value=payload.result_value,
            result_unit=payload.result_unit,
            reference_range=payload.reference_range,
            created_at=datetime.utcnow(),
        )

        self.db.add(result)
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

        lab_request.status = LabRequestStatus.COMPLETED
        lab_request.completed_at = datetime.utcnow()

        self.db.add(lab_request)
        self.db.commit()
        self.db.refresh(lab_request)

        return lab_request


