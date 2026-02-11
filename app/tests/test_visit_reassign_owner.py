import uuid
from datetime import date

import pytest
from fastapi import HTTPException

from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User
from app.models.visit import Visit
from app.services.visit.service import VisitService
from app.shared.enums import Gender, UserRole, VisitServiceLine, VisitStatus


def _create_user(db, *, clinic_id, role: UserRole, label: str) -> User:
    user = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"{label}.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name=label,
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


def _create_visit(db, *, clinic_id, owner_id, service_line: VisitServiceLine) -> Visit:
    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Visit Patient",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.FEMALE,
        phone_number="08000000000",
        address="Test street",
        occupation="Trader",
    )
    db.add(patient)
    db.commit()

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=owner_id,
        status=VisitStatus.REGISTERED,
        service_line=service_line,
        version=1,
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit


def test_reception_can_reassign_any_active_visit(db, clinic_id):
    db.add(Clinic(id=clinic_id, name="Clinic A"))
    db.commit()

    reception = _create_user(
        db,
        clinic_id=clinic_id,
        role=UserRole.RECEPTION,
        label="reception",
    )
    doctor_a = _create_user(
        db,
        clinic_id=clinic_id,
        role=UserRole.DOCTOR,
        label="doctor_a",
    )
    doctor_b = _create_user(
        db,
        clinic_id=clinic_id,
        role=UserRole.DOCTOR,
        label="doctor_b",
    )
    visit = _create_visit(
        db,
        clinic_id=clinic_id,
        owner_id=doctor_a.id,
        service_line=VisitServiceLine.OPD,
    )

    updated = VisitService(db).reassign_owner(
        visit_id=visit.id,
        new_owner_id=doctor_b.id,
        new_service_line=None,
        user=reception,
        expected_version=visit.version,
        reason="handover",
    )

    assert updated.assigned_doctor_id == doctor_b.id
    assert updated.version == 2


def test_assigned_owner_can_reassign_to_colleague(db, clinic_id):
    db.add(Clinic(id=clinic_id, name="Clinic A"))
    db.commit()

    midwife_a = _create_user(
        db,
        clinic_id=clinic_id,
        role=UserRole.MIDWIFE,
        label="midwife_a",
    )
    midwife_b = _create_user(
        db,
        clinic_id=clinic_id,
        role=UserRole.MIDWIFE,
        label="midwife_b",
    )
    visit = _create_visit(
        db,
        clinic_id=clinic_id,
        owner_id=midwife_a.id,
        service_line=VisitServiceLine.MATERNITY,
    )

    updated = VisitService(db).reassign_owner(
        visit_id=visit.id,
        new_owner_id=midwife_b.id,
        new_service_line=None,
        user=midwife_a,
        expected_version=visit.version,
        reason="shift change",
    )

    assert updated.assigned_doctor_id == midwife_b.id


def test_unassigned_owner_cannot_reassign(db, clinic_id):
    db.add(Clinic(id=clinic_id, name="Clinic A"))
    db.commit()

    doctor_a = _create_user(
        db,
        clinic_id=clinic_id,
        role=UserRole.DOCTOR,
        label="doctor_a",
    )
    doctor_b = _create_user(
        db,
        clinic_id=clinic_id,
        role=UserRole.DOCTOR,
        label="doctor_b",
    )
    doctor_c = _create_user(
        db,
        clinic_id=clinic_id,
        role=UserRole.DOCTOR,
        label="doctor_c",
    )
    visit = _create_visit(
        db,
        clinic_id=clinic_id,
        owner_id=doctor_a.id,
        service_line=VisitServiceLine.OPD,
    )

    with pytest.raises(HTTPException) as excinfo:
        VisitService(db).reassign_owner(
            visit_id=visit.id,
            new_owner_id=doctor_c.id,
            new_service_line=None,
            user=doctor_b,
            expected_version=visit.version,
            reason="not assigned",
        )
    assert excinfo.value.status_code == 403


def test_reassign_rejects_wrong_service_line_role(db, clinic_id):
    db.add(Clinic(id=clinic_id, name="Clinic A"))
    db.commit()

    reception = _create_user(
        db,
        clinic_id=clinic_id,
        role=UserRole.RECEPTION,
        label="reception",
    )
    chew = _create_user(
        db,
        clinic_id=clinic_id,
        role=UserRole.CHEW,
        label="chew_a",
    )
    doctor = _create_user(
        db,
        clinic_id=clinic_id,
        role=UserRole.DOCTOR,
        label="doctor_a",
    )
    visit = _create_visit(
        db,
        clinic_id=clinic_id,
        owner_id=chew.id,
        service_line=VisitServiceLine.ANC,
    )

    with pytest.raises(HTTPException) as excinfo:
        VisitService(db).reassign_owner(
            visit_id=visit.id,
            new_owner_id=doctor.id,
            new_service_line=None,
            user=reception,
            expected_version=visit.version,
            reason="invalid role",
        )
    assert excinfo.value.status_code == 400


def test_assigned_chew_can_handover_anc_to_maternity(db, clinic_id):
    db.add(Clinic(id=clinic_id, name="Clinic A"))
    db.commit()

    chew = _create_user(
        db,
        clinic_id=clinic_id,
        role=UserRole.CHEW,
        label="chew_owner",
    )
    midwife = _create_user(
        db,
        clinic_id=clinic_id,
        role=UserRole.MIDWIFE,
        label="midwife_target",
    )
    visit = _create_visit(
        db,
        clinic_id=clinic_id,
        owner_id=chew.id,
        service_line=VisitServiceLine.ANC,
    )

    updated = VisitService(db).reassign_owner(
        visit_id=visit.id,
        new_owner_id=midwife.id,
        new_service_line=VisitServiceLine.MATERNITY,
        user=chew,
        expected_version=visit.version,
        reason="ANC referral to maternity",
    )

    assert updated.service_line == VisitServiceLine.MATERNITY
    assert updated.assigned_doctor_id == midwife.id


def test_assigned_doctor_cannot_change_service_line(db, clinic_id):
    db.add(Clinic(id=clinic_id, name="Clinic A"))
    db.commit()

    doctor = _create_user(
        db,
        clinic_id=clinic_id,
        role=UserRole.DOCTOR,
        label="doctor_owner",
    )
    chew = _create_user(
        db,
        clinic_id=clinic_id,
        role=UserRole.CHEW,
        label="chew_target",
    )
    visit = _create_visit(
        db,
        clinic_id=clinic_id,
        owner_id=doctor.id,
        service_line=VisitServiceLine.OPD,
    )

    with pytest.raises(HTTPException) as excinfo:
        VisitService(db).reassign_owner(
            visit_id=visit.id,
            new_owner_id=chew.id,
            new_service_line=VisitServiceLine.ANC,
            user=doctor,
            expected_version=visit.version,
            reason="invalid handover",
        )
    assert excinfo.value.status_code == 403


def test_reception_can_change_service_line_across_roles(db, clinic_id):
    db.add(Clinic(id=clinic_id, name="Clinic A"))
    db.commit()

    reception = _create_user(
        db,
        clinic_id=clinic_id,
        role=UserRole.RECEPTION,
        label="reception_owner",
    )
    chew = _create_user(
        db,
        clinic_id=clinic_id,
        role=UserRole.CHEW,
        label="chew_owner",
    )
    midwife = _create_user(
        db,
        clinic_id=clinic_id,
        role=UserRole.MIDWIFE,
        label="midwife_target",
    )
    visit = _create_visit(
        db,
        clinic_id=clinic_id,
        owner_id=chew.id,
        service_line=VisitServiceLine.ANC,
    )

    updated = VisitService(db).reassign_owner(
        visit_id=visit.id,
        new_owner_id=midwife.id,
        new_service_line=VisitServiceLine.MATERNITY,
        user=reception,
        expected_version=visit.version,
        reason="front desk handover",
    )

    assert updated.service_line == VisitServiceLine.MATERNITY
    assert updated.assigned_doctor_id == midwife.id
