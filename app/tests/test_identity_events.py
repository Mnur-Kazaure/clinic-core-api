import json
import uuid
from datetime import date

import pytest

from app.models.clinic import Clinic
from app.models.user import User
from app.models.event_log import EventLog
from app.services.event_service import EventService
from app.services.identity_service import IdentityService
from app.schemas.identity import ProvisionalPatientRequest
from app.shared.enums import Gender, UserRole


def test_provisional_creation_emits_event(db, clinic_id):
    clinic = Clinic(id=clinic_id, name="Clinic A")
    db.add(clinic)
    db.commit()

    receptionist = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"reception.{uuid.uuid4()}@example.com",
        password_hash="test",
        role=UserRole.RECEPTION,
        is_active=True,
    )
    db.add(receptionist)
    db.commit()

    service = IdentityService(db)
    payload = ProvisionalPatientRequest(
        full_name="Unknown Patient",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
        created_reason="unconscious arrival",
    )
    patient = service.create_provisional_patient(
        payload=payload,
        current_user=receptionist,
    )

    event = (
        db.query(EventLog)
        .filter(EventLog.event_type == "PROVISIONAL_CREATED")
        .first()
    )
    assert event is not None
    data = json.loads(event.payload)
    assert data["patient_id"] == str(patient.id)


def test_identity_event_emitter_enforced(db, clinic_id):
    service = EventService(db)
    with pytest.raises(ValueError):
        service.emit(
            event_type="IDENTITY_VERIFIED",
            actor_id=uuid.uuid4(),
            actor_role=UserRole.ADMIN,
            clinic_id=clinic_id,
            patient_id=None,
            emitter="clinical",
            payload={"patient_id": str(uuid.uuid4())},
        )
