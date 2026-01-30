import pytest

from app.services.event_service import EventService
from app.models.event_log import EventLog


def test_event_ownership_enforced(db, doctor, clinic_id):
    service = EventService(db)

    # valid emission
    service.emit(
        event_type="ENTRY_DRAFTED",
        actor_id=doctor.id,
        actor_role=doctor.role,
        clinic_id=clinic_id,
        patient_id=None,
        emitter="clinical",
        payload={"entity": "consultation"},
    )
    assert db.query(EventLog).count() == 1

    # invalid emitter for event
    with pytest.raises(ValueError):
        service.emit(
            event_type="ENTRY_DRAFTED",
            actor_id=doctor.id,
            actor_role=doctor.role,
            clinic_id=clinic_id,
            patient_id=None,
            emitter="lab",
            payload={"entity": "consultation"},
        )
