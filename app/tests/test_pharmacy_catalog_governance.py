from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
import uuid

import pytest
from fastapi import HTTPException

from app.models.billing_item import BillingItem
from app.models.clinic import Clinic
from app.models.consultation import Consultation
from app.models.patient import Patient
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.schemas.pharmacy_catalog import (
    PharmacyCatalogRequestCreateRequest,
    PharmacyCatalogRequestReviewRequest,
    PharmacyPricingConfigUpsertRequest,
)
from app.services.pharmacy_catalog_governance_service import (
    PharmacyCatalogGovernanceService,
)
from app.services.pharmacy_inventory_service import PharmacyInventoryService
from app.services.pharmacy_seed_service import PharmacySeedService
from app.services.prescription_service import PrescriptionService
from app.services.service_line_seed_service import ServiceLineSeedService
from app.shared.enums import (
    PharmacyCatalogLifecycleStatus,
    PharmacyInventoryClassification,
    PharmacyInventoryTrackingMode,
    PharmacyPricingStatus,
    UserRole,
    VisitServiceLine,
    VisitStatus,
)


def _seed_governance_context(db, clinic_id: uuid.UUID):
    clinic = Clinic(id=clinic_id, name="Governance Test Clinic")
    db.add(clinic)
    db.flush()

    ServiceLineSeedService(db).seed_default_structure(clinic_id=clinic.id)
    PharmacySeedService(db).seed_kazaure_structure(clinic_id=clinic.id, commit=False)
    db.flush()

    hod = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email="hod@gov.test",
        password_hash="x",
        full_name="Pharmacy HOD",
        role=UserRole.PHARMACY_HOD.value,
        is_active=True,
    )
    cmd = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email="cmd@gov.test",
        password_hash="x",
        full_name="Chief Medical Director",
        role=UserRole.CMD.value,
        is_active=True,
    )
    accountant = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email="accountant@gov.test",
        password_hash="x",
        full_name="Chief Accountant",
        role=UserRole.ACCOUNTANT.value,
        is_active=True,
    )
    doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email="doctor@gov.test",
        password_hash="x",
        full_name="Doctor Demo",
        role=UserRole.DOCTOR.value,
        is_active=True,
    )
    store_officer = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email="store@gov.test",
        password_hash="x",
        full_name="Store Officer",
        role=UserRole.PHARMACY_STORE_OFFICER.value,
        is_active=True,
    )
    db.add_all([hod, cmd, accountant, doctor, store_officer])
    db.flush()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        full_name="Governance Patient",
        date_of_birth=date(1991, 1, 1),
        gender="FEMALE",
        phone_number="08000000001",
        address="Kazaure",
        occupation="Trader",
    )
    db.add(patient)
    db.flush()

    consultation_line = (
        db.query(ServiceLine)
        .filter(
            ServiceLine.clinic_id == clinic.id,
            ServiceLine.name == "Consultation",
        )
        .first()
    )
    assert consultation_line is not None

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.IN_CONSULTATION,
        service_line=VisitServiceLine.OPD,
        service_line_id=consultation_line.id,
        triage_state="PENDING",
    )
    db.add(visit)
    db.flush()

    consultation = Consultation(
        id=uuid.uuid4(),
        visit_id=visit.id,
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        started_at=datetime.now(timezone.utc),
        record_status="SIGNED",
        visit=visit,
    )
    db.add(consultation)
    db.commit()

    return {
        "clinic": clinic,
        "hod": hod,
        "cmd": cmd,
        "accountant": accountant,
        "doctor": doctor,
        "store_officer": store_officer,
        "patient": patient,
        "visit": visit,
        "consultation": consultation,
    }


def _request_payload(**overrides):
    return PharmacyCatalogRequestCreateRequest(
        generic_name="Paracetamol",
        brand_name=None,
        strength="500mg",
        dosage_form="Tablet",
        dispense_unit="Tablet",
        classification=PharmacyInventoryClassification.DRUG,
        tracking_mode=PharmacyInventoryTrackingMode.LOT_TRACKED,
        requires_expiry=True,
        justification="Needed for routine dispensing",
        submit_now=True,
        **overrides,
    )


def _activate_catalog_item(db, ctx, **request_overrides):
    service = PharmacyCatalogGovernanceService(db)
    item = service.create_catalog_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["hod"],
        payload=_request_payload(**request_overrides),
    )
    reviewed = service.review_catalog_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["cmd"],
        item_id=item.id,
        payload=PharmacyCatalogRequestReviewRequest(decision="APPROVE", note="Approved"),
    )
    detail = service.configure_pricing(
        clinic_id=ctx["clinic"].id,
        actor=ctx["accountant"],
        item_id=reviewed.id,
        payload=PharmacyPricingConfigUpsertRequest(
            charge_code=f"PHARM_{uuid.uuid4().hex[:6].upper()}",
            unit_price_minor=15000,
            currency="NGN",
            effective_date=date.today(),
            activate=True,
        ),
    )
    return detail


def test_catalog_duplicate_prevention_is_backend_enforced(db, clinic_id):
    ctx = _seed_governance_context(db, clinic_id)
    service = PharmacyCatalogGovernanceService(db)

    service.create_catalog_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["hod"],
        payload=_request_payload(),
    )

    with pytest.raises(HTTPException) as exc:
        service.create_catalog_request(
            clinic_id=ctx["clinic"].id,
            actor=ctx["hod"],
            payload=_request_payload(),
        )

    assert exc.value.status_code == 409
    assert "already exists" in str(exc.value.detail)


def test_catalog_item_requires_cmd_approval_before_pricing(db, clinic_id):
    ctx = _seed_governance_context(db, clinic_id)
    service = PharmacyCatalogGovernanceService(db)

    item = service.create_catalog_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["hod"],
        payload=_request_payload(),
    )
    assert item.lifecycle_status == PharmacyCatalogLifecycleStatus.AWAITING_CMD_APPROVAL

    with pytest.raises(HTTPException) as exc:
        service.configure_pricing(
            clinic_id=ctx["clinic"].id,
            actor=ctx["accountant"],
            item_id=item.id,
            payload=PharmacyPricingConfigUpsertRequest(
                charge_code="PHARM_PREMATURE",
                unit_price_minor=15000,
                currency="NGN",
                effective_date=date.today(),
                activate=True,
            ),
        )

    assert exc.value.status_code == 409
    assert "CMD approval" in str(exc.value.detail)


def test_no_price_blocks_prescription_billing_creation(db, clinic_id):
    ctx = _seed_governance_context(db, clinic_id)
    service = PharmacyCatalogGovernanceService(db)

    item = service.create_catalog_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["hod"],
        payload=_request_payload(),
    )
    service.review_catalog_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["cmd"],
        item_id=item.id,
        payload=PharmacyCatalogRequestReviewRequest(decision="APPROVE", note="Approved"),
    )

    with pytest.raises(HTTPException) as exc:
        PrescriptionService(db).issue_prescription(
            consultation=ctx["consultation"],
            visit_id=ctx["visit"].id,
            doctor_id=ctx["doctor"].id,
            payload=SimpleNamespace(
                pharmacy_catalog_item_id=item.id,
                drug_name=None,
                dosage="1 tab",
                frequency="bd",
                duration="5 days",
                instructions=None,
            ),
        )

    assert exc.value.status_code == 422
    assert "pricing" in str(exc.value.detail).lower()


def test_price_is_captured_at_billing_creation_and_not_recomputed(db, clinic_id):
    ctx = _seed_governance_context(db, clinic_id)
    detail = _activate_catalog_item(db, ctx)

    first = PrescriptionService(db).issue_prescription(
        consultation=ctx["consultation"],
        visit_id=ctx["visit"].id,
        doctor_id=ctx["doctor"].id,
        payload=SimpleNamespace(
            pharmacy_catalog_item_id=detail.item.id,
            drug_name=None,
            dosage="1 tab",
            frequency="bd",
            duration="5 days",
            quantity_prescribed=5,
            instructions=None,
        ),
    )
    first_billing = first.billing_item_id
    first_item = db.get(BillingItem, first_billing)

    updated = PharmacyCatalogGovernanceService(db).configure_pricing(
        clinic_id=ctx["clinic"].id,
        actor=ctx["accountant"],
        item_id=detail.item.id,
        payload=PharmacyPricingConfigUpsertRequest(
            charge_code=detail.pricing.charge_code,
            unit_price_minor=20000,
            currency="NGN",
            effective_date=date.today(),
            activate=True,
        ),
    )
    assert updated.pricing is not None
    assert updated.pricing.unit_price_minor == 20000

    second = PrescriptionService(db).issue_prescription(
        consultation=ctx["consultation"],
        visit_id=ctx["visit"].id,
        doctor_id=ctx["doctor"].id,
        payload=SimpleNamespace(
            pharmacy_catalog_item_id=detail.item.id,
            drug_name=None,
            dosage="1 tab",
            frequency="bd",
            duration="5 days",
            quantity_prescribed=5,
            instructions=None,
        ),
    )
    second_item = db.get(BillingItem, second.billing_item_id)

    assert first_item is not None
    assert second_item is not None
    assert first_item.unit_price_minor == 15000
    assert second_item.unit_price_minor == 20000


def test_deactivated_item_blocks_new_prescriptions_but_keeps_history(db, clinic_id):
    ctx = _seed_governance_context(db, clinic_id)
    detail = _activate_catalog_item(db, ctx)

    historical = PrescriptionService(db).issue_prescription(
        consultation=ctx["consultation"],
        visit_id=ctx["visit"].id,
        doctor_id=ctx["doctor"].id,
        payload=SimpleNamespace(
            pharmacy_catalog_item_id=detail.item.id,
            drug_name=None,
            dosage="1 tab",
            frequency="bd",
            duration="5 days",
            quantity_prescribed=4,
            instructions=None,
        ),
    )
    assert historical.billing_item_id is not None

    deactivated = PharmacyCatalogGovernanceService(db).configure_pricing(
        clinic_id=ctx["clinic"].id,
        actor=ctx["accountant"],
        item_id=detail.item.id,
        payload=PharmacyPricingConfigUpsertRequest(
            charge_code=detail.pricing.charge_code,
            unit_price_minor=detail.pricing.unit_price_minor,
            currency=detail.pricing.currency,
            effective_date=detail.pricing.effective_date,
            activate=False,
        ),
    )
    assert deactivated.item.lifecycle_status == PharmacyCatalogLifecycleStatus.DEACTIVATED
    assert deactivated.item.billing_status == PharmacyPricingStatus.INACTIVE

    with pytest.raises(HTTPException) as exc:
        PrescriptionService(db).issue_prescription(
            consultation=ctx["consultation"],
            visit_id=ctx["visit"].id,
            doctor_id=ctx["doctor"].id,
            payload=SimpleNamespace(
                pharmacy_catalog_item_id=detail.item.id,
                drug_name=None,
                dosage="1 tab",
                frequency="bd",
                duration="5 days",
                instructions=None,
            ),
        )

    assert exc.value.status_code == 422
    db.refresh(historical)
    assert historical.billing_item_id is not None


def test_store_cannot_create_inventory_master_outside_governance(db, clinic_id):
    ctx = _seed_governance_context(db, clinic_id)

    with pytest.raises(HTTPException) as exc:
        PharmacyInventoryService(db).create_inventory_item(
            clinic_id=ctx["clinic"].id,
            actor=ctx["store_officer"],
            payload=SimpleNamespace(
                generic_name="Ibuprofen",
                dosage_form="Tablet",
                strength="400mg",
                unit_of_measure="Tablet",
                selling_price_minor=10000,
            ),
        )

    assert exc.value.status_code == 403
    assert "CMD approval" in str(exc.value.detail)
