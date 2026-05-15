from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
import uuid

import pytest
from fastapi import HTTPException

from app.models.cashier_pay_point import CashierPayPoint
from app.models.charge_catalog import ChargeCatalog
from app.models.clinic import Clinic
from app.models.consultation import Consultation
from app.models.event_log import EventLog
from app.models.patient import Patient
from app.models.pharmacy_catalog_item import PharmacyCatalogItem
from app.models.pharmacy_inventory_item import PharmacyInventoryItem
from app.models.pharmacy_pricing_config import PharmacyPricingConfig
from app.models.pharmacy_unit_stock_lot import PharmacyUnitStockLot
from app.models.prescription import Prescription
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.services.billing_workflow_service import BillingWorkflowService
from app.services.cashier_pay_point_access_service import CashierPayPointAccessService
from app.services.pharmacy_seed_service import PharmacySeedService
from app.services.pharmacy_service import PharmacyService
from app.services.pharmacy_unit_access_service import PharmacyUnitAccessService
from app.services.prescription_service import PrescriptionService
from app.services.service_line_seed_service import ServiceLineSeedService
from app.services.visit.outstanding import compute_outstanding
from app.shared.enums import (
    BillingItemStatus,
    BillingReasonCode,
    PharmacyCatalogLifecycleStatus,
    PharmacyInventoryClassification,
    PharmacyInventoryTrackingMode,
    PharmacyPricingStatus,
    PharmacyPrescriptionWorkflowStatus,
    PrescriptionStatus,
    RecordStatus,
    UserRole,
    VisitServiceLine,
    VisitStatus,
)


def _seed_governed_catalog_inventory(
    db,
    *,
    clinic_id: uuid.UUID,
    actor_id: uuid.UUID,
    generic_name: str,
    dosage_form: str,
    strength: str | None,
    dispense_unit: str,
    selling_price_minor: int,
    stock_quantity: int,
    low_stock_threshold: int,
    classification: str = PharmacyInventoryClassification.DRUG.value,
    tracking_mode: str = PharmacyInventoryTrackingMode.LOT_TRACKED.value,
    requires_expiry: bool = True,
):
    catalog_item = PharmacyCatalogItem(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        catalog_code=f"PHARM-{uuid.uuid4().hex[:8].upper()}",
        generic_name=generic_name,
        brand_name=None,
        strength=strength,
        dosage_form=dosage_form,
        dispense_unit=dispense_unit,
        classification=classification,
        tracking_mode=tracking_mode,
        requires_expiry=requires_expiry,
        lifecycle_status=PharmacyCatalogLifecycleStatus.ACTIVE.value,
        billing_status=PharmacyPricingStatus.ACTIVE.value,
        active=True,
        justification="Test governance seed",
        requested_by=actor_id,
        submitted_by=actor_id,
        submitted_at=datetime.now(timezone.utc),
        cmd_reviewed_by=actor_id,
        cmd_reviewed_at=datetime.now(timezone.utc),
        cmd_review_note="Approved in test seed",
        priced_by=actor_id,
        priced_at=datetime.now(timezone.utc),
        activated_by=actor_id,
        activated_at=datetime.now(timezone.utc),
    )
    db.add(catalog_item)
    db.flush()

    pricing = PharmacyPricingConfig(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        catalog_item_id=catalog_item.id,
        charge_code=f"PHARM_{uuid.uuid4().hex[:8].upper()}",
        unit_price_minor=selling_price_minor,
        currency="NGN",
        effective_date=datetime.now(timezone.utc).date(),
        status=PharmacyPricingStatus.ACTIVE.value,
        active=True,
        configured_by=actor_id,
        configured_at=datetime.now(timezone.utc),
        activated_by=actor_id,
        activated_at=datetime.now(timezone.utc),
    )
    db.add(pricing)
    db.flush()

    db.add(
        ChargeCatalog(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            code=pricing.charge_code,
            name=f"{generic_name} {strength or ''} {dosage_form}".strip(),
            category=f"PHARMACY_{classification}",
            default_amount_minor=selling_price_minor,
            currency=pricing.currency,
            active=True,
        )
    )

    inventory_item = PharmacyInventoryItem(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        catalog_item_id=catalog_item.id,
        generic_name=generic_name,
        brand_name=None,
        dosage_form=dosage_form,
        strength=strength,
        unit_of_measure=dispense_unit,
        classification=classification,
        tracking_mode=tracking_mode,
        requires_expiry=requires_expiry,
        selling_price_minor=selling_price_minor,
        currency="NGN",
        stock_quantity=stock_quantity,
        low_stock_threshold=low_stock_threshold,
        lifecycle_status="ACTIVE",
        created_by=actor_id,
    )
    db.add(inventory_item)
    db.flush()
    return {
        "catalog_item": catalog_item,
        "pricing_config": pricing,
        "inventory_item": inventory_item,
    }


def _seed_core_context(db, clinic_id: uuid.UUID):
    clinic = Clinic(id=clinic_id, name="Test Clinic")
    db.add(clinic)
    db.flush()

    ServiceLineSeedService(db).seed_default_structure(clinic_id=clinic.id)
    PharmacySeedService(db).seed_kazaure_structure(clinic_id=clinic.id, commit=False)
    db.flush()

    doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email="doctor@pharm.test",
        password_hash="x",
        full_name="Doctor Demo",
        role=UserRole.DOCTOR.value,
        is_active=True,
    )
    cashier = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email="cashier@pharm.test",
        password_hash="x",
        full_name="Cashier Demo",
        role=UserRole.CASHIER.value,
        is_active=True,
    )
    pharmacist = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email="pharmacy@pharm.test",
        password_hash="x",
        full_name="Pharmacist Demo",
        role=UserRole.PHARMACY.value,
        is_active=True,
    )
    db.add_all([doctor, cashier, pharmacist])
    db.flush()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        full_name="Adult Patient",
        date_of_birth=date(1990, 5, 1),
        gender="FEMALE",
        phone_number="08000000000",
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

    adult_unit = (
        db.query(ServiceLine)
        .filter(
            ServiceLine.clinic_id == clinic.id,
            ServiceLine.name == "Adult Pharmacy",
        )
        .first()
    )
    assert adult_unit is not None

    pharmacy_pay_point = (
        db.query(CashierPayPoint)
        .filter(
            CashierPayPoint.clinic_id == clinic.id,
            CashierPayPoint.code == "PHARMACY",
        )
        .first()
    )
    assert pharmacy_pay_point is not None

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

    seeded_item = _seed_governed_catalog_inventory(
        db,
        clinic_id=clinic.id,
        actor_id=pharmacist.id,
        generic_name="Paracetamol",
        dosage_form="Tablet",
        strength="500mg",
        dispense_unit="Tablet",
        selling_price_minor=15000,
        stock_quantity=50,
        low_stock_threshold=10,
    )
    db.commit()

    return {
        "clinic": clinic,
        "doctor": doctor,
        "cashier": cashier,
        "pharmacist": pharmacist,
        "patient": patient,
        "visit": visit,
        "consultation": consultation,
        "catalog_item": seeded_item["catalog_item"],
        "pricing_config": seeded_item["pricing_config"],
        "inventory_item": seeded_item["inventory_item"],
        "adult_unit": adult_unit,
        "pharmacy_pay_point": pharmacy_pay_point,
    }


def test_issue_prescription_creates_medication_billing_and_assignment(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)

    payload = SimpleNamespace(
        drug_name="Paracetamol",
        dosage="1 tab",
        frequency="bd",
        duration="5 days",
        instructions="After meals",
    )
    prescription = PrescriptionService(db).issue_prescription(
        consultation=ctx["consultation"],
        visit_id=ctx["visit"].id,
        doctor_id=ctx["doctor"].id,
        payload=payload,
    )

    db.refresh(prescription)
    assert prescription.billing_item_id is not None
    assert prescription.assigned_dispensing_unit_id == ctx["adult_unit"].id
    assert prescription.assigned_cashier_pay_point_id == ctx["pharmacy_pay_point"].id
    assert prescription.quantity_prescribed == 10
    assert prescription.quantity_dispensed_total == 0
    assert prescription.quantity_remaining == 10
    assert prescription.record_status == RecordStatus.SIGNED
    assert (
        prescription.workflow_status
        == PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE
    )


def test_paying_medication_item_unlocks_ready_to_dispense(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)

    prescription = PrescriptionService(db).issue_prescription(
        consultation=ctx["consultation"],
        visit_id=ctx["visit"].id,
        doctor_id=ctx["doctor"].id,
        payload=SimpleNamespace(
            drug_name="Paracetamol",
            dosage="1 tab",
            frequency="bd",
            duration="5 days",
            quantity_prescribed=5,
            instructions=None,
        ),
    )

    CashierPayPointAccessService(db).sync_user_pay_points(
        clinic_id=ctx["clinic"].id,
        user=ctx["cashier"],
        role=UserRole.CASHIER,
        allowed_pay_point_ids=[ctx["pharmacy_pay_point"].id],
        default_pay_point_id=ctx["pharmacy_pay_point"].id,
    )
    BillingWorkflowService(db).start_shift(
        clinic_id=ctx["clinic"].id,
        cashier_user=ctx["cashier"],
        opening_float_minor=0,
    )
    db.commit()

    result = BillingWorkflowService(db).pay_billing_items(
        clinic_id=ctx["clinic"].id,
        visit_id=ctx["visit"].id,
        billing_item_ids=[prescription.billing_item_id],
        cashier_pay_point_id=ctx["pharmacy_pay_point"].id,
        payment_method=BillingReasonCode.CASH,
        cashier_user=ctx["cashier"],
        notes="Medication payment",
    )

    db.refresh(prescription)
    assert result["paid_item_ids"] == [prescription.billing_item_id]
    assert result["destination_hints"] == [
            {
                "billing_item_id": prescription.billing_item_id,
                "item_name": "Paracetamol 500mg Tablet",
                "service_type": "MEDICATION",
                "destination_label": "Ready for Pharmacy Dispense — Adult Pharmacy",
            "assigned_dispensing_unit_id": ctx["adult_unit"].id,
            "assigned_dispensing_unit_name": "Adult Pharmacy",
            "readiness_state": PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE.value,
        }
    ]
    assert prescription.workflow_status == PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE
    event_types = {
        row.event_type
        for row in db.query(EventLog)
        .filter(
            EventLog.clinic_id == ctx["clinic"].id,
            EventLog.event_type.in_(
                {
                    "PHARMACY_PAYMENT_CAPTURED",
                    "PHARMACY_ITEM_READY_FOR_DISPENSE",
                    "PHARMACY_RECEIPT_CREATED",
                }
            ),
        )
        .all()
    }
    assert event_types == {
        "PHARMACY_PAYMENT_CAPTURED",
        "PHARMACY_ITEM_READY_FOR_DISPENSE",
        "PHARMACY_RECEIPT_CREATED",
    }


def test_dispense_blocks_until_payment_then_deducts_unit_stock(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)
    prescription = PrescriptionService(db).issue_prescription(
        consultation=ctx["consultation"],
        visit_id=ctx["visit"].id,
        doctor_id=ctx["doctor"].id,
        payload=SimpleNamespace(
            drug_name="Paracetamol",
            dosage="1 tab",
            frequency="bd",
            duration="5 days",
            quantity_prescribed=5,
            instructions=None,
        ),
    )

    PharmacyUnitAccessService(db).sync_user_units(
        clinic_id=ctx["clinic"].id,
        user=ctx["pharmacist"],
        role=UserRole.PHARMACY,
        allowed_unit_ids=[ctx["adult_unit"].id],
        default_unit_id=ctx["adult_unit"].id,
    )
    lot = PharmacyUnitStockLot(
        id=uuid.uuid4(),
        clinic_id=ctx["clinic"].id,
        service_line_id=ctx["adult_unit"].id,
        inventory_item_id=ctx["inventory_item"].id,
        batch_number="BATCH-001",
        expiry_date=date(2028, 1, 1),
        quantity_on_hand=20,
    )
    db.add(lot)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        PharmacyService(db).dispense_prescription(
            prescription,
            SimpleNamespace(
                pharmacist_id=ctx["pharmacist"].id,
                quantity=5,
                unit_id=ctx["adult_unit"].id,
                stock_lot_id=lot.id,
            ),
        )
    assert exc.value.status_code == 409

    CashierPayPointAccessService(db).sync_user_pay_points(
        clinic_id=ctx["clinic"].id,
        user=ctx["cashier"],
        role=UserRole.CASHIER,
        allowed_pay_point_ids=[ctx["pharmacy_pay_point"].id],
        default_pay_point_id=ctx["pharmacy_pay_point"].id,
    )
    BillingWorkflowService(db).start_shift(
        clinic_id=ctx["clinic"].id,
        cashier_user=ctx["cashier"],
        opening_float_minor=0,
    )
    db.commit()

    BillingWorkflowService(db).pay_billing_items(
        clinic_id=ctx["clinic"].id,
        visit_id=ctx["visit"].id,
        billing_item_ids=[prescription.billing_item_id],
        cashier_pay_point_id=ctx["pharmacy_pay_point"].id,
        payment_method=BillingReasonCode.CASH,
        cashier_user=ctx["cashier"],
        notes="Medication payment",
    )

    dispensation = PharmacyService(db).dispense_prescription(
        prescription,
        SimpleNamespace(
            pharmacist_id=ctx["pharmacist"].id,
            quantity=5,
            unit_id=ctx["adult_unit"].id,
            stock_lot_id=lot.id,
        ),
    )

    db.refresh(prescription)
    db.refresh(lot)
    assert dispensation.quantity == 5
    assert dispensation.quantity_dispensed_total == 5
    assert dispensation.quantity_remaining == 0
    assert prescription.status == PrescriptionStatus.DISPENSED
    assert prescription.workflow_status == PharmacyPrescriptionWorkflowStatus.DISPENSED
    assert lot.quantity_on_hand == 15


def test_partial_dispense_tracks_remaining_until_final_completion(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)
    prescription = PrescriptionService(db).issue_prescription(
        consultation=ctx["consultation"],
        visit_id=ctx["visit"].id,
        doctor_id=ctx["doctor"].id,
        payload=SimpleNamespace(
            drug_name="Paracetamol",
            dosage="1 tab",
            frequency="bd",
            duration="5 days",
            quantity_prescribed=10,
            instructions=None,
        ),
    )

    PharmacyUnitAccessService(db).sync_user_units(
        clinic_id=ctx["clinic"].id,
        user=ctx["pharmacist"],
        role=UserRole.PHARMACY,
        allowed_unit_ids=[ctx["adult_unit"].id],
        default_unit_id=ctx["adult_unit"].id,
    )
    lot = PharmacyUnitStockLot(
        id=uuid.uuid4(),
        clinic_id=ctx["clinic"].id,
        service_line_id=ctx["adult_unit"].id,
        inventory_item_id=ctx["inventory_item"].id,
        batch_number="BATCH-PARTIAL-001",
        expiry_date=date(2028, 1, 1),
        quantity_on_hand=12,
    )
    db.add(lot)

    CashierPayPointAccessService(db).sync_user_pay_points(
        clinic_id=ctx["clinic"].id,
        user=ctx["cashier"],
        role=UserRole.CASHIER,
        allowed_pay_point_ids=[ctx["pharmacy_pay_point"].id],
        default_pay_point_id=ctx["pharmacy_pay_point"].id,
    )
    BillingWorkflowService(db).start_shift(
        clinic_id=ctx["clinic"].id,
        cashier_user=ctx["cashier"],
        opening_float_minor=0,
    )
    db.commit()

    BillingWorkflowService(db).pay_billing_items(
        clinic_id=ctx["clinic"].id,
        visit_id=ctx["visit"].id,
        billing_item_ids=[prescription.billing_item_id],
        cashier_pay_point_id=ctx["pharmacy_pay_point"].id,
        payment_method=BillingReasonCode.CASH,
        cashier_user=ctx["cashier"],
        notes="Medication payment",
    )

    partial = PharmacyService(db).dispense_prescription(
        prescription,
        SimpleNamespace(
            pharmacist_id=ctx["pharmacist"].id,
            quantity=6,
            unit_id=ctx["adult_unit"].id,
            stock_lot_id=lot.id,
        ),
    )

    db.refresh(prescription)
    db.refresh(lot)
    assert partial.quantity == 6
    assert partial.quantity_dispensed_total == 6
    assert partial.quantity_remaining == 4
    assert prescription.status == PrescriptionStatus.ISSUED
    assert (
        prescription.workflow_status
        == PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED
    )
    assert prescription.quantity_dispensed_total == 6
    assert prescription.quantity_remaining == 4
    assert lot.quantity_on_hand == 6
    assert (
        db.query(EventLog)
        .filter(EventLog.event_type == "PHARMACY_PARTIAL_DISPENSED")
        .count()
        == 1
    )
    assert compute_outstanding(db, visit_id=ctx["visit"].id)[
        "unfulfilled_prescriptions_count"
    ] == 1

    completion = PharmacyService(db).dispense_prescription(
        prescription,
        SimpleNamespace(
            pharmacist_id=ctx["pharmacist"].id,
            quantity=4,
            unit_id=ctx["adult_unit"].id,
            stock_lot_id=lot.id,
        ),
    )

    db.refresh(prescription)
    db.refresh(lot)
    assert completion.quantity == 4
    assert completion.quantity_dispensed_total == 10
    assert completion.quantity_remaining == 0
    assert prescription.status == PrescriptionStatus.DISPENSED
    assert prescription.workflow_status == PharmacyPrescriptionWorkflowStatus.DISPENSED
    assert prescription.quantity_dispensed_total == 10
    assert prescription.quantity_remaining == 0
    assert lot.quantity_on_hand == 2
    assert (
        db.query(EventLog)
        .filter(EventLog.event_type == "PHARMACY_FULLY_DISPENSED")
        .count()
        == 1
    )
    assert compute_outstanding(db, visit_id=ctx["visit"].id)[
        "unfulfilled_prescriptions_count"
    ] == 0


def test_cannot_cancel_paid_prescription_without_refund(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)
    prescription = PrescriptionService(db).issue_prescription(
        consultation=ctx["consultation"],
        visit_id=ctx["visit"].id,
        doctor_id=ctx["doctor"].id,
        payload=SimpleNamespace(
            drug_name="Paracetamol",
            dosage="1 tab",
            frequency="bd",
            duration="5 days",
            instructions=None,
        ),
    )

    CashierPayPointAccessService(db).sync_user_pay_points(
        clinic_id=ctx["clinic"].id,
        user=ctx["cashier"],
        role=UserRole.CASHIER,
        allowed_pay_point_ids=[ctx["pharmacy_pay_point"].id],
        default_pay_point_id=ctx["pharmacy_pay_point"].id,
    )
    BillingWorkflowService(db).start_shift(
        clinic_id=ctx["clinic"].id,
        cashier_user=ctx["cashier"],
        opening_float_minor=0,
    )
    db.commit()

    BillingWorkflowService(db).pay_billing_items(
        clinic_id=ctx["clinic"].id,
        visit_id=ctx["visit"].id,
        billing_item_ids=[prescription.billing_item_id],
        cashier_pay_point_id=ctx["pharmacy_pay_point"].id,
        payment_method=BillingReasonCode.CASH,
        cashier_user=ctx["cashier"],
        notes="Medication payment",
    )

    with pytest.raises(HTTPException) as exc:
        PrescriptionService(db).cancel_prescription(
            prescription=prescription,
            reason="Duplicate order",
        )
    assert exc.value.status_code == 409


def test_reassignment_preserves_ready_state_and_changes_unit_only(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)
    prescription = PrescriptionService(db).issue_prescription(
        consultation=ctx["consultation"],
        visit_id=ctx["visit"].id,
        doctor_id=ctx["doctor"].id,
        payload=SimpleNamespace(
            drug_name="Paracetamol",
            dosage="1 tab",
            frequency="bd",
            duration="5 days",
            instructions=None,
        ),
    )

    target_unit = (
        db.query(ServiceLine)
        .filter(
            ServiceLine.clinic_id == ctx["clinic"].id,
            ServiceLine.name == "GOPD Pharmacy",
        )
        .first()
    )
    assert target_unit is not None

    CashierPayPointAccessService(db).sync_user_pay_points(
        clinic_id=ctx["clinic"].id,
        user=ctx["cashier"],
        role=UserRole.CASHIER,
        allowed_pay_point_ids=[ctx["pharmacy_pay_point"].id],
        default_pay_point_id=ctx["pharmacy_pay_point"].id,
    )
    BillingWorkflowService(db).start_shift(
        clinic_id=ctx["clinic"].id,
        cashier_user=ctx["cashier"],
        opening_float_minor=0,
    )
    db.commit()

    BillingWorkflowService(db).pay_billing_items(
        clinic_id=ctx["clinic"].id,
        visit_id=ctx["visit"].id,
        billing_item_ids=[prescription.billing_item_id],
        cashier_pay_point_id=ctx["pharmacy_pay_point"].id,
        payment_method=BillingReasonCode.CASH,
        cashier_user=ctx["cashier"],
    )

    result = PharmacyService(db).reassign_prescription(
        prescription=prescription,
        actor=ctx["pharmacist"],
        target_unit_id=target_unit.id,
        reason="Out of stock in current unit",
        note="Move to GOPD",
    )

    db.refresh(prescription)
    assert result["previous_unit_id"] == ctx["adult_unit"].id
    assert result["target_unit_id"] == target_unit.id
    assert prescription.assigned_dispensing_unit_id == target_unit.id
    assert prescription.workflow_status == PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE
