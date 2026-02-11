# app/services/lab_request_service.py
import uuid
from app.models.lab_request import LabRequest
from app.shared.enums import LabRequestStatus
from app.services.event_service import EventService


# Service for managing lab requests
class LabRequestService:
    def __init__(self, db):
        self.db = db
        self.event_service = EventService(db)

    def create_request(self, visit, test_name, doctor_id, special_instructions=None):
        existing = (
            self.db.query(LabRequest)
            .filter(
                LabRequest.visit_id == visit.id,
                LabRequest.test_name == test_name,
                LabRequest.status == LabRequestStatus.PENDING,
            )
            .first()
        )

        if existing:
            return existing

        lab_request = LabRequest(
            id=uuid.uuid4(),
            visit_id=visit.id,
            clinic_id=visit.clinic_id,
            test_name=test_name,
            special_instructions=special_instructions,
            requested_by=doctor_id,
            status=LabRequestStatus.PENDING,
        )

        self.db.add(lab_request)
        self.db.commit()
        self.db.refresh(lab_request)

        self.event_service.emit(
            event_type="LAB_ORDERED",
            actor_id=doctor_id,
            actor_role="DOCTOR",
            clinic_id=visit.clinic_id,
            patient_id=visit.patient_id,
            emitter="lab",
            payload={
                "lab_request_id": str(lab_request.id),
                "visit_id": str(visit.id),
                "test_name": lab_request.test_name,
                "special_instructions": lab_request.special_instructions,
            },
        )

        return lab_request
