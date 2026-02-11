import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException

from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User
from app.models.visit import Visit
from app.services.pmr_service import PMRService
from app.shared.enums import Gender, PurposeOfUse, UserRole, VisitStatus


def test_pmr_access_rules_reception_and_doctor(db, clinic_id):
    clinic = Clinic(id=clinic_id, name="Clinic A")
    db.add(clinic)
    db.commit()

    reception = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"reception.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Reception",
        role=UserRole.RECEPTION,
        is_active=True,
    )
    doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"doctor.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Doctor",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    chew = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"chew.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="CHEW",
        role=UserRole.CHEW,
        is_active=True,
    )
    midwife = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"midwife.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Midwife",
        role=UserRole.MIDWIFE,
        is_active=True,
    )
    db.add(reception)
    db.add(doctor)
    db.add(chew)
    db.add(midwife)
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="PMR Patient",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    db.add(patient)
    db.commit()

    service = PMRService(db)

    service.get_pmr(
        patient_id=patient.id,
        clinic_id=clinic_id,
        actor=reception,
        purpose_of_use=PurposeOfUse.OPERATIONS,
        justification="ok",
        break_glass=False,
    )

    with pytest.raises(HTTPException) as excinfo:
        service.get_pmr(
            patient_id=patient.id,
            clinic_id=clinic_id,
            actor=doctor,
            purpose_of_use=PurposeOfUse.TREATMENT,
            justification="ok",
            break_glass=False,
        )
    assert excinfo.value.status_code == 403

    with pytest.raises(HTTPException) as excinfo:
        service.get_pmr(
            patient_id=patient.id,
            clinic_id=clinic_id,
            actor=chew,
            purpose_of_use=PurposeOfUse.TREATMENT,
            justification="ok",
            break_glass=False,
        )
    assert excinfo.value.status_code == 403

    with pytest.raises(HTTPException) as excinfo:
        service.get_pmr(
            patient_id=patient.id,
            clinic_id=clinic_id,
            actor=midwife,
            purpose_of_use=PurposeOfUse.TREATMENT,
            justification="ok",
            break_glass=False,
        )
    assert excinfo.value.status_code == 403

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.REGISTERED,
        started_at=datetime.now(timezone.utc),
    )
    db.add(visit)
    db.commit()

    service.get_pmr(
        patient_id=patient.id,
        clinic_id=clinic_id,
        actor=doctor,
        purpose_of_use=PurposeOfUse.TREATMENT,
        justification="assigned visit access",
        break_glass=False,
    )

    # Completing the visit clears the "active context" requirement for clinicians.
    visit.status = VisitStatus.COMPLETED
    db.commit()

    anc_visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=chew.id,
        status=VisitStatus.REGISTERED,
        started_at=datetime.now(timezone.utc),
    )
    db.add(anc_visit)
    db.commit()

    service.get_pmr(
        patient_id=patient.id,
        clinic_id=clinic_id,
        actor=chew,
        purpose_of_use=PurposeOfUse.TREATMENT,
        justification="ANC follow-up",
        break_glass=False,
    )

    anc_visit.status = VisitStatus.COMPLETED
    db.commit()

    mat_visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=midwife.id,
        status=VisitStatus.REGISTERED,
        started_at=datetime.now(timezone.utc),
    )
    db.add(mat_visit)
    db.commit()

    service.get_pmr(
        patient_id=patient.id,
        clinic_id=clinic_id,
        actor=midwife,
        purpose_of_use=PurposeOfUse.TREATMENT,
        justification="maternity history check",
        break_glass=False,
    )
