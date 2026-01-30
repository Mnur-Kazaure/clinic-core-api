import json
import uuid
from datetime import datetime, timezone, date

import pytest

from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.visit import Visit
from app.models.event_log import EventLog
from app.services.clinical_priority_service import ClinicalPriorityService
from app.services.event_service import EventService
from app.shared.enums import (
    ClinicalPriorityLevel,
    ClinicalPrioritySource,
    VisitStatus,
    Gender,
    UserRole,
)
from app.schemas.clinical_priority import ClinicalPriorityCreateRequest


def test_priority_escalation_emits_event(db, clinic_id):
    clinic = Clinic(id=clinic_id, name="Clinic A")
    db.add(clinic)
    db.commit()

    doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"doc.{uuid.uuid4()}@example.com",
        password_hash="test",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db.add(doctor)
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Priority Patient",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    db.add(patient)
    db.commit()

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.IN_CONSULTATION,
        started_at=datetime.now(timezone.utc),
    )
    db.add(visit)
    db.commit()

    payload = ClinicalPriorityCreateRequest(
        level=ClinicalPriorityLevel.CRITICAL,
        source=ClinicalPrioritySource.CLINICIAN,
        reason="requires immediate review",
    )
    service = ClinicalPriorityService(db)
    service.set_priority(
        visit_id=visit.id,
        level=payload.level,
        source=payload.source,
        reason=payload.reason,
        current_user=doctor,
    )

    event = (
        db.query(EventLog)
        .filter(EventLog.event_type == "PRIORITY_ESCALATED")
        .first()
    )
    assert event is not None
    data = json.loads(event.payload)
    assert data["visit_id"] == str(visit.id)
    assert data["patient_id"] == str(patient.id)
    assert data["clinic_id"] == str(clinic_id)
    assert data["from_level"] == ClinicalPriorityLevel.ROUTINE.value
    assert data["to_level"] == ClinicalPriorityLevel.CRITICAL.value
    assert data["reason"] == "requires immediate review"


def test_priority_event_emitter_enforced(db, clinic_id):
    service = EventService(db)
    with pytest.raises(ValueError):
        service.emit(
            event_type="PRIORITY_ESCALATED",
            actor_id=uuid.uuid4(),
            actor_role=UserRole.DOCTOR,
            clinic_id=clinic_id,
            patient_id=None,
            emitter="clinical",
            payload={"visit_id": str(uuid.uuid4())},
        )
