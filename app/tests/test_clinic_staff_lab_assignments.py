import uuid

import pytest
from fastapi import HTTPException

from app.models.clinic import Clinic
from app.models.service_line import ServiceLine
from app.models.user import User
from app.services.clinic_service.service import ClinicService
from app.shared.enums import ServiceLineKind, UserRole


def _seed_clinic_admin(db, clinic_id: uuid.UUID) -> User:
    clinic = Clinic(id=clinic_id, name="KSH Test Clinic")
    admin = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email="admin@ksh.example.com",
        password_hash="hashed",
        full_name="Clinic Admin",
        role=UserRole.CLINIC_ADMIN.value,
        is_active=True,
    )
    db.add_all([clinic, admin])
    db.commit()
    return admin


def _seed_lab_units(db, clinic_id: uuid.UUID) -> tuple[ServiceLine, ServiceLine]:
    lab_root = ServiceLine(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Medical Laboratory",
        parent_id=None,
        department_id=None,
        requires_doctor=False,
        service_line_kind=ServiceLineKind.LAB_UNIT,
        is_active=True,
    )
    hematology = ServiceLine(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Haematology",
        parent_id=lab_root.id,
        department_id=None,
        requires_doctor=False,
        service_line_kind=ServiceLineKind.LAB_UNIT,
        is_active=True,
    )
    microbiology = ServiceLine(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Microbiology",
        parent_id=lab_root.id,
        department_id=None,
        requires_doctor=False,
        service_line_kind=ServiceLineKind.LAB_UNIT,
        is_active=True,
    )
    db.add_all([lab_root, hematology, microbiology])
    db.commit()
    return hematology, microbiology


def test_create_lab_staff_with_allowed_units(db):
    clinic_id = uuid.uuid4()
    admin = _seed_clinic_admin(db, clinic_id)
    hematology, microbiology = _seed_lab_units(db, clinic_id)

    payload = type(
        "Payload",
        (),
        {
                "full_name": "Lab Tech A",
                "email": "lab.tech@ksh.example.com",
            "password": "StrongPass123",
            "role": UserRole.LAB_TECH,
            "allowed_lab_unit_ids": [hematology.id, microbiology.id],
            "default_lab_unit_id": microbiology.id,
        },
    )()

    user = ClinicService(db).create_staff_user(payload=payload, current_user=admin)

    db.refresh(user)
    response = ClinicService(db)._build_staff_response(user=user)

    assert user.role == UserRole.LAB_TECH.value
    assert user.default_lab_unit_id == microbiology.id
    assert [unit.name for unit in response.allowed_lab_units] == [
        "Haematology",
        "Microbiology",
    ]
    assert response.default_lab_unit_name == "Microbiology"


def test_create_lab_staff_requires_leaf_unit_assignment(db):
    clinic_id = uuid.uuid4()
    admin = _seed_clinic_admin(db, clinic_id)
    clinic_service = ClinicService(db)

    lab_root = ServiceLine(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Medical Laboratory",
        parent_id=None,
        department_id=None,
        requires_doctor=False,
        service_line_kind=ServiceLineKind.LAB_UNIT,
        is_active=True,
    )
    hematology = ServiceLine(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Haematology",
        parent_id=lab_root.id,
        department_id=None,
        requires_doctor=False,
        service_line_kind=ServiceLineKind.LAB_UNIT,
        is_active=True,
    )
    db.add_all([lab_root, hematology])
    db.commit()

    payload = type(
        "Payload",
        (),
        {
                "full_name": "Lab Tech B",
                "email": "lab.tech.b@ksh.example.com",
            "password": "StrongPass123",
            "role": UserRole.LAB_TECH,
            "allowed_lab_unit_ids": [lab_root.id],
            "default_lab_unit_id": lab_root.id,
        },
    )()

    with pytest.raises(HTTPException) as exc:
        clinic_service.create_staff_user(payload=payload, current_user=admin)

    assert exc.value.status_code == 422
    assert exc.value.detail == "Lab unit assignments must target active leaf service lines"


def test_create_lab_manager_does_not_require_unit_assignment(db):
    clinic_id = uuid.uuid4()
    admin = _seed_clinic_admin(db, clinic_id)

    payload = type(
        "Payload",
        (),
        {
                "full_name": "Lab HOD",
                "email": "lab.manager@ksh.example.com",
            "password": "StrongPass123",
            "role": UserRole.LAB_MANAGER,
            "allowed_lab_unit_ids": [],
            "default_lab_unit_id": None,
        },
    )()

    user = ClinicService(db).create_staff_user(payload=payload, current_user=admin)
    response = ClinicService(db)._build_staff_response(user=user)

    assert user.role == UserRole.LAB_MANAGER.value
    assert user.default_lab_unit_id is None
    assert response.allowed_lab_units == []
