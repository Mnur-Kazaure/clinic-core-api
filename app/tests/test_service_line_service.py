import uuid

import pytest
from fastapi import HTTPException

from app.models.clinic import Clinic
from app.models.department import Department
from app.services.service_line_service import ServiceLineService
from app.shared.enums import ServiceLineKind


def _seed_clinic(db, clinic_id):
    clinic = Clinic(
        id=clinic_id,
        name="Test Clinic",
    )
    db.add(clinic)
    db.commit()


def test_update_allows_clearing_nullable_fields(db, clinic_id):
    _seed_clinic(db, clinic_id)
    gopd = Department(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="GOPD",
    )
    db.add(gopd)
    db.commit()

    service = ServiceLineService(db)
    root = service.create(
        clinic_id=clinic_id,
        name="GOPD",
        parent_id=None,
        department_id=gopd.id,
        default_child_id=None,
        requires_doctor=True,
        service_line_kind=ServiceLineKind.GENERAL,
        is_active=True,
    )
    consultation = service.create(
        clinic_id=clinic_id,
        name="Consultation",
        parent_id=root.id,
        department_id=None,
        default_child_id=None,
        requires_doctor=True,
        service_line_kind=ServiceLineKind.GENERAL,
        is_active=True,
    )

    updated = service.update(
        clinic_id=clinic_id,
        service_line_id=root.id,
        default_child_id=consultation.id,
    )
    assert updated.default_child_id == consultation.id
    assert updated.department_id == gopd.id

    updated = service.update(
        clinic_id=clinic_id,
        service_line_id=root.id,
        default_child_id=None,
        department_id=None,
    )
    assert updated.default_child_id is None
    assert updated.department_id is None


def test_update_allows_promoting_child_to_root(db, clinic_id):
    _seed_clinic(db, clinic_id)
    service = ServiceLineService(db)

    root = service.create(
        clinic_id=clinic_id,
        name="Specialist",
        parent_id=None,
        department_id=None,
        default_child_id=None,
        requires_doctor=True,
        service_line_kind=ServiceLineKind.GENERAL,
        is_active=True,
    )
    sub_line = service.create(
        clinic_id=clinic_id,
        name="Cardiology",
        parent_id=root.id,
        department_id=None,
        default_child_id=None,
        requires_doctor=True,
        service_line_kind=ServiceLineKind.GENERAL,
        is_active=True,
    )

    updated = service.update(
        clinic_id=clinic_id,
        service_line_id=sub_line.id,
        parent_id=None,
    )
    assert updated.parent_id is None


def test_update_rejects_blank_name(db, clinic_id):
    _seed_clinic(db, clinic_id)
    service = ServiceLineService(db)

    line = service.create(
        clinic_id=clinic_id,
        name="A&E",
        parent_id=None,
        department_id=None,
        default_child_id=None,
        requires_doctor=False,
        service_line_kind=ServiceLineKind.GENERAL,
        is_active=True,
    )

    with pytest.raises(HTTPException) as exc:
        service.update(
            clinic_id=clinic_id,
            service_line_id=line.id,
            name="   ",
        )
    assert exc.value.status_code == 400
    assert exc.value.detail == "name cannot be empty"
