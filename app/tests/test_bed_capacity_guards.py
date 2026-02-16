from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.guards.bed_guards import (
    require_bed_capacity_admin,
    require_bed_management_role,
)
from app.shared.enums import UserRole


def _user(role: UserRole) -> SimpleNamespace:
    return SimpleNamespace(role=role)


def test_require_bed_management_role_allows_admin_and_clinic_admin():
    assert require_bed_management_role(_user(UserRole.ADMIN)).role == UserRole.ADMIN
    assert (
        require_bed_management_role(_user(UserRole.CLINIC_ADMIN)).role
        == UserRole.CLINIC_ADMIN
    )


def test_require_bed_management_role_rejects_other_roles():
    with pytest.raises(HTTPException) as exc:
        require_bed_management_role(_user(UserRole.DOCTOR))

    assert exc.value.status_code == 403
    assert exc.value.detail == "Bed management access denied"


def test_require_bed_capacity_admin_allows_only_clinic_admin():
    assert (
        require_bed_capacity_admin(_user(UserRole.CLINIC_ADMIN)).role
        == UserRole.CLINIC_ADMIN
    )

    with pytest.raises(HTTPException) as exc:
        require_bed_capacity_admin(_user(UserRole.ADMIN))

    assert exc.value.status_code == 403
    assert exc.value.detail == "Clinic Admin access required for capacity changes"
