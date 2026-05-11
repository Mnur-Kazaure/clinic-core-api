from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api.v1.lab_query_parsing import parse_optional_iso_date
from app.services.lab_manager_governance_service import LabManagerGovernanceService
from app.tests.test_lab_manager_governance_service import _seed_manager_context


def test_lab_manager_dashboard_service_returns_dashboard(db):
    context = _seed_manager_context(db)

    payload = LabManagerGovernanceService(db).get_dashboard(
        clinic_id=context["clinic"].id,
        start_date=parse_optional_iso_date("2026-03-19", field_name="start_date"),
        end_date=parse_optional_iso_date("2026-03-19", field_name="end_date"),
    )

    assert payload.overview.total_tests_today >= 0
    assert payload.units
    assert payload.staff


def test_parse_optional_iso_date_rejects_invalid_dates():
    with pytest.raises(HTTPException) as exc:
        parse_optional_iso_date("19-03-2026", field_name="start_date")

    assert exc.value.status_code == 422
    assert exc.value.detail == "start_date must use YYYY-MM-DD format"
