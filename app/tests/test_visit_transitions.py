import pytest
from app.services.visit.guards import guard_can_transition
from app.shared.enums import VisitStatus
from app.models.lab_request import LabRequest
from app.models.prescription import Prescription
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
