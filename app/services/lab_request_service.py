# app/services/lab_request_service.py
import uuid
from app.models.lab_request import LabRequest
from app.shared.enums import LabRequestStatus


# Service for managing lab requests
class LabRequestService:
    def __init__(self, db):
        self.db = db

    def create_request(self, visit, test_name, doctor_id):
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
            test_name=test_name,
            requested_by=doctor_id,
            status=LabRequestStatus.PENDING,
        )

        self.db.add(lab_request)
        self.db.commit()
        self.db.refresh(lab_request)

        return lab_request