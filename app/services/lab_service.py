# app/services/lab_service.py
from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from datetime import datetime
import uuid

from datetime import datetime
from app.shared.enums import VisitStatus
from app.services.visit.service import VisitService

from app.core.system_actor import SystemUser

class LabService:
    def __init__(self, db):
        self.db = db
        self.visit_service = VisitService(db)



    def record_result(self, visit, payload):
        lab_request = (
            self.db.query(LabRequest)
            .filter(LabRequest.visit_id == visit.id)
            .first()
        )

        if not lab_request:
            raise ValueError("No lab request found for visit")

        result = LabResult(
            id=uuid.uuid4(),
            lab_request_id=lab_request.id,
            result_value=payload.result_value,
            result_unit=payload.result_unit,
            reference_range=payload.reference_range,
            technician_id=payload.technician_id,
            created_at=datetime.utcnow(),
        )

        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)

        return result
    




    def complete_lab(self, lab_request):
        # Mark lab as completed
        lab_request.completed_at = datetime.utcnow()
        lab_request.status = "COMPLETED"

        self.db.add(lab_request)
        self.db.commit()

        # 🔒 Auto-advance visit (single source of truth)
        self.visit_service.transition_visit(
            visit_id=lab_request.visit_id,
            to_status=VisitStatus.LAB_COMPLETED,
            user=SystemUser,
        )
