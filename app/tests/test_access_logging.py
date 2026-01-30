import uuid
from datetime import date
import pytest

from app.models.access_log import AccessLog
from app.models.event_log import EventLog
from app.models.patient import Patient
from app.models.visit import Visit
from app.services.access_log_service import AccessLogService
from app.models.event_log import EventLog
from app.shared.enums import VisitStatus, Gender


def _seed_patient_visit(db, clinic_id, doctor_id):
    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Audit Patient",
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
        assigned_doctor_id=doctor_id,
        status=VisitStatus.IN_CONSULTATION,
    )
    db.add(visit)
    db.commit()
    return patient, visit


def test_access_logged_search_and_chart_read(db, doctor, clinic_id):
    service = AccessLogService(db)

    patient, visit = _seed_patient_visit(db, clinic_id, doctor.id)

    service.log_search(
        actor=doctor,
        clinic_id=clinic_id,
        purpose_of_use="clinical_care",
        reason="patient lookup",
    )

    service.log_chart_read(
        actor=doctor,
        clinic_id=clinic_id,
        patient_id=patient.id,
        purpose_of_use="clinical_care",
        reason="chart review",
    )

    access_logs = db.query(AccessLog).all()
    event_logs = db.query(EventLog).filter(EventLog.event_type == "ACCESS_LOGGED").all()

    assert len(access_logs) == 2
    assert len(event_logs) == 2

    chart_log = next(log for log in access_logs if log.action == "CHART_READ")
    assert chart_log.patient_id == patient.id


def test_break_glass_requires_reason(db, doctor, clinic_id):
    service = AccessLogService(db)

    with pytest.raises(ValueError):
        service.log_break_glass(
            actor=doctor,
            clinic_id=clinic_id,
            patient_id=uuid.uuid4(),
            purpose_of_use="clinical_care",
            reason="",
        )


def test_break_glass_emits_event(db, doctor, clinic_id):
    service = AccessLogService(db)
    patient, _ = _seed_patient_visit(db, clinic_id, doctor.id)

    service.log_break_glass(
        actor=doctor,
        clinic_id=clinic_id,
        patient_id=patient.id,
        purpose_of_use="clinical_care",
        reason="emergency override",
    )

    event_logs = db.query(EventLog).filter(EventLog.event_type == "BREAK_GLASS_USED").all()
    assert len(event_logs) == 1
