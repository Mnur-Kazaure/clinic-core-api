import pytest
from app.services.visit.guards import guard_can_transition
from app.shared.enums import VisitStatus, UserRole
from app.models.user import User
import uuid

def test_triaged_transition_is_contract_driven(db, chew, visit_registered):
    with pytest.raises(PermissionError):
        guard_can_transition(
            db=db,
            visit=visit_registered,
            to_status=VisitStatus.TRIAGED,
            user=chew,
        )


def test_invalid_transition_registered_to_lab_fails(db, receptionist, visit_registered):
    with pytest.raises(ValueError):
        guard_can_transition(
            db=db,
            visit=visit_registered,
            to_status=VisitStatus.LAB_REQUESTED,
            user=receptionist,
        )


def test_assigned_doctor_can_transition_registered_to_in_consultation(
    db,
    doctor,
    visit_registered,
):
    guard_can_transition(
        db=db,
        visit=visit_registered,
        to_status=VisitStatus.IN_CONSULTATION,
        user=doctor,
    )


def test_unassigned_doctor_cannot_transition_registered_to_in_consultation(
    db,
    clinic_id,
    visit_registered,
):
    other_doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"other_doctor_{clinic_id}@example.test",
        password_hash="test",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db.add(other_doctor)
    db.commit()

    with pytest.raises(PermissionError, match="Only assigned clinical owner can start consultation"):
        guard_can_transition(
            db=db,
            visit=visit_registered,
            to_status=VisitStatus.IN_CONSULTATION,
            user=other_doctor,
        )
