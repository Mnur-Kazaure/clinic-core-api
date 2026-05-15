"""Seed deterministic users for Playwright role-matrix smoke tests.

This script is idempotent:
- creates/updates one clinic
- creates/updates RECEPTION, CHEW, MIDWIFE, DOCTOR, LAB, PHARMACY, PHARMACY_HOD,
  PHARMACY_STORE_OFFICER, and ADMIN users by email
"""

from __future__ import annotations

import argparse
import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace

import bcrypt

from app.core.database import SessionLocal
from app.models.consultation import Consultation
from app.models.clinic import Clinic
from app.models.billing_item import BillingItem
from app.models.cashier_pay_point import CashierPayPoint
from app.models.charge_catalog import ChargeCatalog
from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.models.lab_specimen import LabSpecimen
from app.models.patient import Patient
from app.models.pharmacy_catalog_item import PharmacyCatalogItem
from app.models.pharmacy_inventory_item import PharmacyInventoryItem
from app.models.pharmacy_issue_voucher import PharmacyIssueVoucher
from app.models.pharmacy_issue_voucher_item import PharmacyIssueVoucherItem
from app.models.pharmacy_pricing_config import PharmacyPricingConfig
from app.models.pharmacy_unit_profile import PharmacyUnitProfile
from app.models.pharmacy_unit_stock_lot import PharmacyUnitStockLot
from app.models.prescription import Prescription
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.services.billing_workflow_service import BillingWorkflowService
from app.services.cashier_pay_point_access_service import CashierPayPointAccessService
from app.services.lab_catalog_seed_service import LabCatalogSeedService
from app.services.lab_foundation_service import LabFoundationService
from app.services.lab_request_service import LabRequestService
from app.services.lab_safety_service import LabSafetyService
from app.services.lab_unit_access_service import LabUnitAccessService
from app.services.pharmacy_seed_service import PharmacySeedService
from app.services.pharmacy_supply_service import PharmacySupplyService
from app.services.pharmacy_unit_access_service import PharmacyUnitAccessService
from app.services.prescription_service import PrescriptionService
from app.services.service_line_seed_service import ServiceLineSeedService
from app.services.visit.service import VisitService
from app.schemas.lab_foundation import LabSpecimenCreate
from app.schemas.lab_safety import LabResultReleaseRequest, StructuredLabResultCreate
from app.shared.enums import (
    BillingItemStatus,
    BillingReasonCode,
    Gender,
    LabResultLifecycleStatus,
    LabSpecimenStatus,
    LabRequestStatus,
    PharmacyCatalogLifecycleStatus,
    PharmacyInventoryClassification,
    PharmacyIssueVoucherStatus,
    PharmacyInventoryTrackingMode,
    PharmacyPricingStatus,
    PharmacyPrescriptionWorkflowStatus,
    PharmacyUnitCategory,
    PrescriptionStatus,
    ServiceLineKind,
    UserRole,
    VisitServiceLine,
    VisitStatus,
)


PLAYWRIGHT_LAB_REQUEST_NOTE = "Playwright lab workflow seed"
PLAYWRIGHT_LAB_COMPLETION_NOTE = "Playwright lab completion seed"
PLAYWRIGHT_PHARMACY_WORKFLOW_PATIENT_NAME = "Playwright Pharmacy Workflow Patient"
PLAYWRIGHT_PHARMACY_WORKFLOW_PHONE = "08000000099"
PLAYWRIGHT_PHARMACY_WORKFLOW_BATCH = "PW-PHARM-001"
PLAYWRIGHT_PHARMACY_WORKFLOW_STOCK_QTY = 40
PLAYWRIGHT_PHARMACY_RETURN_ITEM = "Playwright Return Flow Commodity"
PLAYWRIGHT_PHARMACY_RETURN_BATCH = "PW-RETURN-001"
PLAYWRIGHT_PHARMACY_RETURN_ISSUED_QTY = 8


def _display_catalog_name(
    generic_name: str,
    strength: str | None,
    dosage_form: str,
) -> str:
    return " ".join(part for part in [generic_name, strength or "", dosage_form] if part).strip()


def _ensure_governed_inventory_item(
    db,
    *,
    clinic: Clinic,
    actor: User,
    generic_name: str,
    brand_name: str | None,
    dosage_form: str,
    strength: str | None,
    unit_of_measure: str,
    classification: str,
    tracking_mode: str,
    requires_expiry: bool,
    selling_price_minor: int,
    currency: str,
    stock_quantity: int,
    low_stock_threshold: int,
) -> PharmacyInventoryItem:
    catalog_item = (
        db.query(PharmacyCatalogItem)
        .filter(
            PharmacyCatalogItem.clinic_id == clinic.id,
            PharmacyCatalogItem.generic_name == generic_name,
            PharmacyCatalogItem.dosage_form == dosage_form,
            PharmacyCatalogItem.strength == strength,
            PharmacyCatalogItem.dispense_unit == unit_of_measure,
        )
        .first()
    )
    now = datetime.now(timezone.utc)
    if catalog_item is None:
        catalog_item = PharmacyCatalogItem(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            catalog_code=f"PHARM-{uuid.uuid4().hex[:8].upper()}",
            generic_name=generic_name,
            brand_name=brand_name,
            strength=strength,
            dosage_form=dosage_form,
            dispense_unit=unit_of_measure,
            classification=classification,
            tracking_mode=tracking_mode,
            requires_expiry=requires_expiry,
            lifecycle_status=PharmacyCatalogLifecycleStatus.ACTIVE.value,
            billing_status=PharmacyPricingStatus.ACTIVE.value,
            active=True,
            justification="Playwright pharmacy seed",
            requested_by=actor.id,
            submitted_by=actor.id,
            submitted_at=now,
            cmd_reviewed_by=actor.id,
            cmd_reviewed_at=now,
            cmd_review_note="Approved in Playwright seed",
            priced_by=actor.id,
            priced_at=now,
            activated_by=actor.id,
            activated_at=now,
        )
        db.add(catalog_item)
        db.flush()
    else:
        catalog_item.brand_name = brand_name
        catalog_item.strength = strength
        catalog_item.dispense_unit = unit_of_measure
        catalog_item.classification = classification
        catalog_item.tracking_mode = tracking_mode
        catalog_item.requires_expiry = requires_expiry
        catalog_item.lifecycle_status = PharmacyCatalogLifecycleStatus.ACTIVE.value
        catalog_item.billing_status = PharmacyPricingStatus.ACTIVE.value
        catalog_item.active = True
        catalog_item.priced_by = actor.id
        catalog_item.priced_at = now
        catalog_item.activated_by = actor.id
        catalog_item.activated_at = now
        db.add(catalog_item)
        db.flush()

    pricing = (
        db.query(PharmacyPricingConfig)
        .filter(
            PharmacyPricingConfig.clinic_id == clinic.id,
            PharmacyPricingConfig.catalog_item_id == catalog_item.id,
        )
        .first()
    )
    charge_code = catalog_item.catalog_code.replace("-", "_")
    if pricing is None:
        pricing = PharmacyPricingConfig(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            catalog_item_id=catalog_item.id,
            charge_code=charge_code,
            unit_price_minor=selling_price_minor,
            currency=currency,
            effective_date=now.date(),
            status=PharmacyPricingStatus.ACTIVE.value,
            active=True,
            configured_by=actor.id,
            configured_at=now,
            activated_by=actor.id,
            activated_at=now,
        )
        db.add(pricing)
    else:
        pricing.charge_code = charge_code
        pricing.unit_price_minor = selling_price_minor
        pricing.currency = currency
        pricing.effective_date = now.date()
        pricing.status = PharmacyPricingStatus.ACTIVE.value
        pricing.active = True
        pricing.configured_by = actor.id
        pricing.configured_at = now
        pricing.activated_by = actor.id
        pricing.activated_at = now
        pricing.deactivated_by = None
        pricing.deactivated_at = None
        db.add(pricing)
    db.flush()

    charge = (
        db.query(ChargeCatalog)
        .filter(
            ChargeCatalog.clinic_id == clinic.id,
            ChargeCatalog.code == charge_code,
        )
        .first()
    )
    if charge is None:
        charge = ChargeCatalog(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            code=charge_code,
            name=_display_catalog_name(generic_name, strength, dosage_form),
            category=f"PHARMACY_{classification}",
            default_amount_minor=selling_price_minor,
            currency=currency,
            active=True,
        )
    else:
        charge.name = _display_catalog_name(generic_name, strength, dosage_form)
        charge.category = f"PHARMACY_{classification}"
        charge.default_amount_minor = selling_price_minor
        charge.currency = currency
        charge.active = True
    db.add(charge)
    db.flush()

    inventory_item = (
        db.query(PharmacyInventoryItem)
        .filter(
            PharmacyInventoryItem.clinic_id == clinic.id,
            PharmacyInventoryItem.generic_name == generic_name,
            PharmacyInventoryItem.dosage_form == dosage_form,
            PharmacyInventoryItem.strength == strength,
            PharmacyInventoryItem.unit_of_measure == unit_of_measure,
        )
        .first()
    )
    if inventory_item is None:
        inventory_item = PharmacyInventoryItem(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            catalog_item_id=catalog_item.id,
            generic_name=generic_name,
            brand_name=brand_name,
            dosage_form=dosage_form,
            strength=strength,
            unit_of_measure=unit_of_measure,
            classification=classification,
            tracking_mode=tracking_mode,
            requires_expiry=requires_expiry,
            selling_price_minor=selling_price_minor,
            currency=currency,
            stock_quantity=stock_quantity,
            low_stock_threshold=low_stock_threshold,
            lifecycle_status="ACTIVE",
            created_by=actor.id,
            updated_by=actor.id,
        )
        db.add(inventory_item)
    else:
        inventory_item.catalog_item_id = catalog_item.id
        inventory_item.brand_name = brand_name
        inventory_item.classification = classification
        inventory_item.tracking_mode = tracking_mode
        inventory_item.requires_expiry = requires_expiry
        inventory_item.selling_price_minor = selling_price_minor
        inventory_item.currency = currency
        inventory_item.stock_quantity = max(int(inventory_item.stock_quantity), stock_quantity)
        inventory_item.low_stock_threshold = low_stock_threshold
        inventory_item.lifecycle_status = "ACTIVE"
        inventory_item.updated_by = actor.id
        db.add(inventory_item)
    db.flush()
    return inventory_item


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed Playwright e2e users")
    parser.add_argument("--clinic-name", default="Playwright E2E Clinic")
    parser.add_argument("--reception-email", required=True)
    parser.add_argument("--reception-password", required=True)
    parser.add_argument("--chew-email", required=True)
    parser.add_argument("--chew-password", required=True)
    parser.add_argument("--midwife-email", required=True)
    parser.add_argument("--midwife-password", required=True)
    parser.add_argument("--doctor-email", default=None)
    parser.add_argument("--doctor-password", default=None)
    parser.add_argument("--lab-email", default=None)
    parser.add_argument("--lab-password", default=None)
    parser.add_argument("--pharmacy-email", default=None)
    parser.add_argument("--pharmacy-password", default=None)
    parser.add_argument("--cmd-email", default=None)
    parser.add_argument("--cmd-password", default=None)
    parser.add_argument("--pharmacy-hod-email", default=None)
    parser.add_argument("--pharmacy-hod-password", default=None)
    parser.add_argument("--pharmacy-store-email", default=None)
    parser.add_argument("--pharmacy-store-password", default=None)
    parser.add_argument("--admin-email", default=None)
    parser.add_argument("--admin-password", default=None)
    parser.add_argument(
        "--pharmacy-workflow-patient-name",
        default=PLAYWRIGHT_PHARMACY_WORKFLOW_PATIENT_NAME,
    )
    parser.add_argument(
        "--pharmacy-workflow-phone-number",
        default=PLAYWRIGHT_PHARMACY_WORKFLOW_PHONE,
    )
    parser.add_argument(
        "--pharmacy-workflow-batch-number",
        default=PLAYWRIGHT_PHARMACY_WORKFLOW_BATCH,
    )
    parser.add_argument(
        "--pharmacy-workflow-stock-quantity",
        type=int,
        default=PLAYWRIGHT_PHARMACY_WORKFLOW_STOCK_QTY,
    )
    parser.add_argument(
        "--pharmacy-workflow-prescribed-quantity",
        type=int,
        default=10,
    )
    parser.add_argument(
        "--pharmacy-return-item-name",
        default=PLAYWRIGHT_PHARMACY_RETURN_ITEM,
    )
    parser.add_argument(
        "--pharmacy-return-batch-number",
        default=PLAYWRIGHT_PHARMACY_RETURN_BATCH,
    )
    parser.add_argument(
        "--pharmacy-return-issued-quantity",
        type=int,
        default=PLAYWRIGHT_PHARMACY_RETURN_ISSUED_QTY,
    )
    return parser.parse_args()


def _upsert_user(
    db,
    *,
    clinic_id,
    email: str,
    password: str,
    full_name: str,
    role_value: str,
) -> None:
    user = db.query(User).filter(User.email == email).first()
    password_hash = _hash_password(password)
    if user:
        user.clinic_id = clinic_id
        user.full_name = full_name
        user.role = role_value
        user.password_hash = password_hash
        user.is_active = True
        return

    db.add(
        User(
            clinic_id=clinic_id,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            role=role_value,
            is_active=True,
        )
        )


def _hash_password(password: str) -> str:
    # Keep seeding independent from passlib backend quirks in CI.
    truncated = password.encode("utf-8")[:72]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode("utf-8")


def _derive_colleague_email(email: str) -> str:
    local, domain = email.split("@", 1)
    return f"{local}+colleague@{domain}"


def _derive_admin_email(email: str) -> str:
    local, domain = email.split("@", 1)
    return f"{local}+admin@{domain}"


def _derive_cashier_email(email: str) -> str:
    return _derive_role_email(email, "cashier")


def _derive_role_email(email: str, suffix: str) -> str:
    local, domain = email.split("@", 1)
    return f"{local}+{suffix}@{domain}"


def _resolve_role_value(primary: str, fallback: str | None = None) -> str:
    """Use newer role when available, otherwise fall back for older branches."""
    role = getattr(UserRole, primary, None)
    if role is not None:
        return role.value
    if fallback is None:
        raise AttributeError(f"UserRole.{primary} is not available and no fallback was provided")
    return getattr(UserRole, fallback).value


def _get_user_by_email(db, email: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise RuntimeError(f"Seeded user not found: {email}")
    return user


def _ensure_paid_lab_request(
    db,
    *,
    clinic: Clinic,
    doctor: User,
    cashier_user: User,
    patient_name: str,
    phone_number: str,
    note: str,
) -> LabRequest:
    patient = (
        db.query(Patient)
        .filter(
            Patient.clinic_id == clinic.id,
            Patient.full_name == patient_name,
            Patient.phone_number == phone_number,
        )
        .first()
    )
    if patient is None:
        patient = Patient(
            clinic_id=clinic.id,
            full_name=patient_name,
            date_of_birth=date(1992, 1, 1),
            gender=Gender.MALE,
            phone_number=phone_number,
            address="Playwright Workflow Address",
            occupation="Trader",
        )
        db.add(patient)
        db.flush()

    request = (
        db.query(LabRequest)
        .filter(
            LabRequest.clinic_id == clinic.id,
            LabRequest.test_code == "CHEM_RBS",
            LabRequest.special_instructions == note,
            LabRequest.status == LabRequestStatus.PENDING,
        )
        .order_by(LabRequest.created_at.desc())
        .first()
    )
    if request is None:
        visit = Visit(
            clinic_id=clinic.id,
            patient_id=patient.id,
            assigned_doctor_id=doctor.id,
            status=VisitStatus.IN_CONSULTATION,
            started_at=datetime.now(timezone.utc),
            version=1,
        )
        db.add(visit)
        db.flush()
        request = LabRequestService(db).create_request(
            visit=visit,
            test_name="Random Blood Sugar (RBS)",
            test_code="CHEM_RBS",
            doctor_id=doctor.id,
            special_instructions=note,
            actor=doctor,
        )

    visit = db.query(Visit).filter(Visit.id == request.visit_id).first()
    if visit is None:
        raise RuntimeError("Playwright lab workflow visit was not created")
    if visit.status == VisitStatus.IN_CONSULTATION:
        VisitService(db).transition_visit(
            visit_id=visit.id,
            to_status=VisitStatus.LAB_REQUESTED,
            user=doctor,
            expected_version=visit.version,
        )
        db.flush()

    billing_item = (
        db.query(BillingItem)
        .filter(BillingItem.id == request.billing_item_id)
        .first()
    )
    if billing_item is None:
        raise RuntimeError("Playwright lab workflow billing item was not created")

    cashier_role = getattr(cashier_user.role, "value", cashier_user.role)
    if cashier_role == UserRole.CASHIER.value:
        billing_service = BillingWorkflowService(db)
        if billing_service.get_current_shift(clinic_id=clinic.id, cashier_user=cashier_user) is None:
            billing_service.start_shift(
                clinic_id=clinic.id,
                cashier_user=cashier_user,
                opening_float_minor=0,
            )

    if billing_item.status != BillingItemStatus.PAID:
        BillingWorkflowService(db).pay_billing_items(
            clinic_id=clinic.id,
            visit_id=request.visit_id,
            billing_item_ids=[billing_item.id],
            payment_method=BillingReasonCode.CASH,
            cashier_user=cashier_user,
        )
    db.flush()
    return request


def _ensure_completion_ready_request(
    db,
    *,
    clinic: Clinic,
    doctor: User,
    lab_user: User,
    supervisor_user: User,
    cashier_user: User,
) -> None:
    request = _ensure_paid_lab_request(
        db,
        clinic=clinic,
        doctor=doctor,
        cashier_user=cashier_user,
        patient_name="Playwright Lab Completion Patient",
        phone_number="08000000088",
        note=PLAYWRIGHT_LAB_COMPLETION_NOTE,
    )
    foundation_service = LabFoundationService(db)
    safety_service = LabSafetyService(db)

    ready_specimen = (
        db.query(LabSpecimen)
        .filter(
            LabSpecimen.request_item_id == request.id,
            LabSpecimen.status.in_(
                [LabSpecimenStatus.RECEIVED, LabSpecimenStatus.IN_PROCESS]
            ),
        )
        .first()
    )
    if ready_specimen is None:
        foundation_service.create_specimen(
            lab_request=request,
            actor_id=lab_user.id,
            payload=LabSpecimenCreate(
                specimen_type="Blood",
                specimen_source="Blood",
                container_type="Fluoride oxalate / plain tube",
                status=LabSpecimenStatus.RECEIVED,
            ),
        )

    result = (
        db.query(LabResult)
        .filter(LabResult.request_item_id == request.id)
        .order_by(LabResult.created_at.desc())
        .first()
    )
    if result is None:
        template = foundation_service.get_request_template(lab_request=request)
        numeric_field = next(
            (field for field in template["fields"] if str(field.field_type) == "NUMBER"),
            template["fields"][0],
        )
        result = safety_service.submit_structured_result(
            lab_request=request,
            actor_id=lab_user.id,
            payload=StructuredLabResultCreate(
                values=[
                    {
                        "template_field_id": numeric_field.id,
                        "value_number": 120,
                    }
                ]
            ),
        )

    if result.status not in (
        LabResultLifecycleStatus.VERIFIED,
        LabResultLifecycleStatus.RELEASED,
        LabResultLifecycleStatus.AMENDED,
    ):
        result = safety_service.verify_result(
            result_id=result.id,
            clinic_id=clinic.id,
            actor_id=supervisor_user.id,
        )
    if result.status not in (
        LabResultLifecycleStatus.RELEASED,
        LabResultLifecycleStatus.AMENDED,
    ):
        safety_service.release_result(
            result_id=result.id,
            clinic_id=clinic.id,
            actor_id=supervisor_user.id,
            payload=LabResultReleaseRequest(),
        )
    db.flush()


def _ensure_lab_workflow_seed(
    db,
    *,
    clinic: Clinic,
    doctor: User,
    lab_user: User,
    supervisor_user: User,
    cashier_user: User,
) -> None:
    ServiceLineSeedService(db).seed_default_structure(clinic_id=clinic.id)
    LabCatalogSeedService(db).seed_kazaure_catalog(clinic_id=clinic.id)
    db.flush()

    chemical_unit = (
        db.query(ServiceLine)
        .filter(
            ServiceLine.clinic_id == clinic.id,
            ServiceLine.service_line_kind == ServiceLineKind.LAB_UNIT,
            ServiceLine.name == "Chemical Pathology",
            ServiceLine.is_active.is_(True),
        )
        .first()
    )
    if chemical_unit is None:
        raise RuntimeError("Chemical Pathology unit was not seeded for Playwright lab workflow")

    try:
        lab_role = UserRole(lab_user.role)
    except ValueError:
        lab_role = UserRole.LAB

    LabUnitAccessService(db).sync_user_units(
        clinic_id=clinic.id,
        user=lab_user,
        role=lab_role,
        allowed_unit_ids=[chemical_unit.id],
        default_unit_id=chemical_unit.id,
    )
    db.flush()

    try:
        supervisor_role = UserRole(supervisor_user.role)
    except ValueError:
        supervisor_role = UserRole.LAB_SUPERVISOR

    LabUnitAccessService(db).sync_user_units(
        clinic_id=clinic.id,
        user=supervisor_user,
        role=supervisor_role,
        allowed_unit_ids=[chemical_unit.id],
        default_unit_id=chemical_unit.id,
    )
    db.flush()

    _ensure_paid_lab_request(
        db,
        clinic=clinic,
        doctor=doctor,
        cashier_user=cashier_user,
        patient_name="Playwright Lab Workflow Patient",
        phone_number="08000000077",
        note=PLAYWRIGHT_LAB_REQUEST_NOTE,
    )
    _ensure_completion_ready_request(
        db,
        clinic=clinic,
        doctor=doctor,
        lab_user=lab_user,
        supervisor_user=supervisor_user,
        cashier_user=cashier_user,
    )
    db.commit()


def _ensure_pharmacy_workflow_seed(
    db,
    *,
    clinic: Clinic,
    pharmacist_user: User,
    cashier_user: User,
    doctor_user: User,
    patient_name: str,
    phone_number: str,
    batch_number: str,
    stock_quantity: int,
    prescribed_quantity: int,
) -> None:
    ServiceLineSeedService(db).seed_default_structure(clinic_id=clinic.id)
    PharmacySeedService(db).seed_kazaure_structure(clinic_id=clinic.id, commit=False)
    db.flush()

    adult_unit = (
        db.query(ServiceLine)
        .filter(
            ServiceLine.clinic_id == clinic.id,
            ServiceLine.service_line_kind == ServiceLineKind.PHARMACY_UNIT,
            ServiceLine.name == "Adult Pharmacy",
            ServiceLine.is_active.is_(True),
        )
        .first()
    )
    if adult_unit is None:
        raise RuntimeError("Adult Pharmacy unit was not seeded for Playwright pharmacy workflow")

    pharmacy_pay_point = (
        db.query(CashierPayPoint)
        .filter(
            CashierPayPoint.clinic_id == clinic.id,
            CashierPayPoint.code == "PHARMACY",
            CashierPayPoint.is_active.is_(True),
        )
        .first()
    )
    if pharmacy_pay_point is None:
        raise RuntimeError("Pharmacy pay point was not seeded for Playwright cashier workflow")

    try:
        pharmacy_role = UserRole(pharmacist_user.role)
    except ValueError:
        pharmacy_role = UserRole.PHARMACY

    PharmacyUnitAccessService(db).sync_user_units(
        clinic_id=clinic.id,
        user=pharmacist_user,
        role=pharmacy_role,
        allowed_unit_ids=[adult_unit.id],
        default_unit_id=adult_unit.id,
    )
    db.flush()

    try:
        cashier_role = UserRole(cashier_user.role)
    except ValueError:
        cashier_role = UserRole.CASHIER

    CashierPayPointAccessService(db).sync_user_pay_points(
        clinic_id=clinic.id,
        user=cashier_user,
        role=cashier_role,
        allowed_pay_point_ids=[pharmacy_pay_point.id],
        default_pay_point_id=pharmacy_pay_point.id,
    )

    billing_service = BillingWorkflowService(db)
    if billing_service.get_current_shift(clinic_id=clinic.id, cashier_user=cashier_user) is None:
        billing_service.start_shift(
            clinic_id=clinic.id,
            cashier_user=cashier_user,
            opening_float_minor=0,
        )
        db.flush()

    patient = (
        db.query(Patient)
        .filter(
            Patient.clinic_id == clinic.id,
            Patient.full_name == patient_name,
            Patient.phone_number == phone_number,
        )
        .first()
    )
    if patient is None:
        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name=patient_name,
            date_of_birth=date(1991, 1, 1),
            gender=Gender.FEMALE,
            phone_number=phone_number,
            address="Playwright Pharmacy Workflow Address",
            occupation="Trader",
        )
        db.add(patient)
        db.flush()

    inventory_item = _ensure_governed_inventory_item(
        db,
        clinic=clinic,
        actor=pharmacist_user,
        generic_name="Paracetamol",
        brand_name=None,
        dosage_form="Tablet",
        strength="500mg",
        unit_of_measure="Tablet",
        classification=PharmacyInventoryClassification.DRUG.value,
        tracking_mode=PharmacyInventoryTrackingMode.LOT_TRACKED.value,
        requires_expiry=True,
        selling_price_minor=15000,
        currency="NGN",
        stock_quantity=stock_quantity,
        low_stock_threshold=10,
    )

    stock_lot = (
        db.query(PharmacyUnitStockLot)
        .filter(
            PharmacyUnitStockLot.clinic_id == clinic.id,
            PharmacyUnitStockLot.service_line_id == adult_unit.id,
            PharmacyUnitStockLot.inventory_item_id == inventory_item.id,
            PharmacyUnitStockLot.batch_number == batch_number,
        )
        .first()
    )
    if stock_lot is None:
        stock_lot = PharmacyUnitStockLot(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            service_line_id=adult_unit.id,
            inventory_item_id=inventory_item.id,
            batch_number=batch_number,
            expiry_date=date(2028, 1, 1),
            quantity_on_hand=stock_quantity,
        )
        db.add(stock_lot)
    else:
        stock_lot.expiry_date = date(2028, 1, 1)
        stock_lot.quantity_on_hand = stock_quantity
        db.add(stock_lot)
    db.flush()

    existing_workflow = (
        db.query(Prescription)
        .join(BillingItem, BillingItem.id == Prescription.billing_item_id)
        .filter(
            Prescription.clinic_id == clinic.id,
            Prescription.drug_name == "Paracetamol",
            Prescription.assigned_dispensing_unit_id == adult_unit.id,
            Prescription.status == PrescriptionStatus.ISSUED,
            Prescription.workflow_status
            == PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE,
            Prescription.quantity_prescribed == prescribed_quantity,
            BillingItem.status == BillingItemStatus.PENDING,
            BillingItem.cashier_pay_point_id == pharmacy_pay_point.id,
            BillingItem.patient_id == patient.id,
        )
        .order_by(Prescription.issued_at.desc())
        .first()
    )
    if existing_workflow is not None:
        db.commit()
        return

    consultation_line = (
        db.query(ServiceLine)
        .filter(
            ServiceLine.clinic_id == clinic.id,
            ServiceLine.name == "Consultation",
            ServiceLine.is_active.is_(True),
        )
        .first()
    )
    if consultation_line is None:
        raise RuntimeError("Consultation service line was not seeded for Playwright pharmacy workflow")

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        patient_id=patient.id,
        assigned_doctor_id=doctor_user.id,
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
        doctor_id=doctor_user.id,
        started_at=datetime.now(timezone.utc),
        record_status="SIGNED",
        visit=visit,
    )
    db.add(consultation)
    db.flush()

    PrescriptionService(db).issue_prescription(
        consultation=consultation,
        visit_id=visit.id,
        doctor_id=doctor_user.id,
        payload=SimpleNamespace(
            drug_name="Paracetamol",
            dosage="1 tab",
            frequency="bd",
            duration="5 days",
            quantity_prescribed=prescribed_quantity,
            instructions="Playwright pharmacy workflow seed",
        ),
    )
    db.commit()


def _ensure_return_to_store_seed(
    db,
    *,
    clinic: Clinic,
    pharmacist_user: User,
    cmd_user: User,
    store_user: User,
    item_name: str,
    batch_number: str,
    issued_quantity: int,
) -> None:
    ServiceLineSeedService(db).seed_default_structure(clinic_id=clinic.id)
    PharmacySeedService(db).seed_kazaure_structure(clinic_id=clinic.id, commit=False)
    db.flush()

    adult_unit = (
        db.query(ServiceLine)
        .filter(
            ServiceLine.clinic_id == clinic.id,
            ServiceLine.service_line_kind == ServiceLineKind.PHARMACY_UNIT,
            ServiceLine.name == "Adult Pharmacy",
            ServiceLine.is_active.is_(True),
        )
        .first()
    )
    if adult_unit is None:
        raise RuntimeError("Adult Pharmacy unit was not seeded for Playwright return workflow")

    store_unit = (
        db.query(ServiceLine)
        .join(
            PharmacyUnitProfile,
            PharmacyUnitProfile.service_line_id == ServiceLine.id,
        )
        .filter(
            ServiceLine.clinic_id == clinic.id,
            ServiceLine.service_line_kind == ServiceLineKind.PHARMACY_UNIT,
            ServiceLine.is_active.is_(True),
            PharmacyUnitProfile.unit_category == PharmacyUnitCategory.STORE,
        )
        .first()
    )
    if store_unit is None:
        raise RuntimeError("Store unit was not seeded for Playwright return workflow")

    try:
        pharmacy_role = UserRole(pharmacist_user.role)
    except ValueError:
        pharmacy_role = UserRole.PHARMACY

    PharmacyUnitAccessService(db).sync_user_units(
        clinic_id=clinic.id,
        user=pharmacist_user,
        role=pharmacy_role,
        allowed_unit_ids=[adult_unit.id],
        default_unit_id=adult_unit.id,
    )
    db.flush()

    inventory_item = _ensure_governed_inventory_item(
        db,
        clinic=clinic,
        actor=store_user,
        generic_name=item_name,
        brand_name=None,
        dosage_form="Pack",
        strength=None,
        unit_of_measure="Pack",
        classification=PharmacyInventoryClassification.CONSUMABLE.value,
        tracking_mode=PharmacyInventoryTrackingMode.LOT_TRACKED.value,
        requires_expiry=True,
        selling_price_minor=2500,
        currency="NGN",
        stock_quantity=max(issued_quantity * 2, issued_quantity),
        low_stock_threshold=5,
    )

    existing_voucher = (
        db.query(PharmacyIssueVoucher)
        .join(PharmacyIssueVoucherItem, PharmacyIssueVoucherItem.voucher_id == PharmacyIssueVoucher.id)
        .filter(
            PharmacyIssueVoucher.clinic_id == clinic.id,
            PharmacyIssueVoucher.receiving_unit_id == adult_unit.id,
            PharmacyIssueVoucher.status.in_(
                (
                    PharmacyIssueVoucherStatus.ACKNOWLEDGED.value,
                    PharmacyIssueVoucherStatus.CLOSED.value,
                )
            ),
            PharmacyIssueVoucherItem.inventory_item_id == inventory_item.id,
            PharmacyIssueVoucherItem.batch_number == batch_number,
        )
        .order_by(PharmacyIssueVoucher.issued_at.desc().nullslast())
        .first()
    )
    if existing_voucher is not None:
        db.commit()
        return

    store_lot = (
        db.query(PharmacyUnitStockLot)
        .filter(
            PharmacyUnitStockLot.clinic_id == clinic.id,
            PharmacyUnitStockLot.service_line_id == store_unit.id,
            PharmacyUnitStockLot.inventory_item_id == inventory_item.id,
            PharmacyUnitStockLot.batch_number == batch_number,
        )
        .first()
    )
    if store_lot is None:
        store_lot = PharmacyUnitStockLot(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            service_line_id=store_unit.id,
            inventory_item_id=inventory_item.id,
            batch_number=batch_number,
            expiry_date=date(2029, 1, 1),
            quantity_on_hand=max(issued_quantity * 2, issued_quantity),
        )
        db.add(store_lot)
    else:
        store_lot.expiry_date = date(2029, 1, 1)
        store_lot.quantity_on_hand = max(int(store_lot.quantity_on_hand), issued_quantity * 2)
        db.add(store_lot)
    db.flush()

    supply = PharmacySupplyService(db)
    refill_request = supply.create_refill_request(
        clinic_id=clinic.id,
        actor=pharmacist_user,
        payload=SimpleNamespace(
            unit_id=adult_unit.id,
            urgency="ROUTINE",
            note=f"Playwright return workflow seed for {item_name}",
            items=[
                SimpleNamespace(
                    inventory_item_id=inventory_item.id,
                    requested_quantity=issued_quantity,
                    note="Deterministic return-to-store seed",
                )
            ],
        ),
    )
    reviewed = supply.review_refill_request(
        clinic_id=clinic.id,
        actor=cmd_user,
        request_id=refill_request["id"],
        payload=SimpleNamespace(decision="APPROVE", review_note=None, items=None),
    )
    voucher = supply.create_issue_voucher(
        clinic_id=clinic.id,
        actor=store_user,
        payload=SimpleNamespace(
            refill_request_id=reviewed["id"],
            store_unit_id=store_unit.id,
            note=f"Playwright return workflow seed for {item_name}",
            items=[
                SimpleNamespace(
                    refill_request_item_id=reviewed["items"][0]["id"],
                    batch_number=batch_number,
                    expiry_date=date(2029, 1, 1),
                    issued_quantity=issued_quantity,
                )
            ],
        ),
    )
    dispatched = supply.dispatch_issue_voucher(
        clinic_id=clinic.id,
        actor=store_user,
        voucher_id=voucher["id"],
        payload=SimpleNamespace(note="Playwright return workflow dispatch"),
    )
    supply.acknowledge_issue_voucher(
        clinic_id=clinic.id,
        actor=pharmacist_user,
        voucher_id=dispatched["id"],
        payload=SimpleNamespace(
            unit_id=adult_unit.id,
            note="Playwright return workflow acknowledgement",
            items=[
                SimpleNamespace(
                    voucher_item_id=dispatched["items"][0]["id"],
                    received_quantity=issued_quantity,
                )
            ],
        ),
    )
    db.commit()


def main() -> None:
    args = _parse_args()
    doctor_email = args.doctor_email or _derive_role_email(args.reception_email, "doctor")
    doctor_password = args.doctor_password or args.reception_password
    lab_email = args.lab_email or _derive_role_email(args.reception_email, "lab")
    lab_password = args.lab_password or args.reception_password
    pharmacy_email = args.pharmacy_email or _derive_role_email(
        args.reception_email, "pharmacy"
    )
    pharmacy_password = args.pharmacy_password or args.reception_password
    cmd_email = args.cmd_email or _derive_role_email(args.reception_email, "cmd")
    cmd_password = args.cmd_password or args.reception_password
    pharmacy_hod_email = args.pharmacy_hod_email or _derive_role_email(
        args.reception_email, "pharmacy-hod"
    )
    pharmacy_hod_password = args.pharmacy_hod_password or args.reception_password
    pharmacy_store_email = args.pharmacy_store_email or _derive_role_email(
        args.reception_email, "pharmacy-store"
    )
    pharmacy_store_password = args.pharmacy_store_password or args.reception_password
    admin_email = args.admin_email or _derive_admin_email(args.reception_email)
    admin_password = args.admin_password or args.reception_password
    cashier_email = _derive_cashier_email(args.reception_email)
    cashier_password = args.reception_password
    supervisor_email = _derive_role_email(args.reception_email, "lab-supervisor")
    supervisor_password = args.reception_password
    db = SessionLocal()
    try:
        clinic = db.query(Clinic).filter(Clinic.name == args.clinic_name).first()
        if not clinic:
            clinic = Clinic(name=args.clinic_name, billing_currency="NGN")
            db.add(clinic)
            db.flush()

        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=args.reception_email,
            password=args.reception_password,
            full_name="E2E Reception",
            role_value=UserRole.RECEPTION.value,
        )
        chew_role_value = _resolve_role_value("CHEW", "DOCTOR")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=args.chew_email,
            password=args.chew_password,
            full_name="E2E CHEW",
            role_value=chew_role_value,
        )
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=_derive_colleague_email(args.chew_email),
            password=args.chew_password,
            full_name="E2E CHEW Colleague",
            role_value=chew_role_value,
        )
        midwife_role_value = _resolve_role_value("MIDWIFE", "LAB")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=args.midwife_email,
            password=args.midwife_password,
            full_name="E2E Midwife",
            role_value=midwife_role_value,
        )
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=_derive_colleague_email(args.midwife_email),
            password=args.midwife_password,
            full_name="E2E Midwife Colleague",
            role_value=midwife_role_value,
        )
        doctor_role_value = _resolve_role_value("DOCTOR", "CHEW")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=doctor_email,
            password=doctor_password,
            full_name="E2E Doctor",
            role_value=doctor_role_value,
        )
        lab_role_value = _resolve_role_value("LAB", "MIDWIFE")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=lab_email,
            password=lab_password,
            full_name="E2E Lab Technician",
            role_value=lab_role_value,
        )
        supervisor_role_value = _resolve_role_value("LAB_SUPERVISOR", "LAB")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=supervisor_email,
            password=supervisor_password,
            full_name="E2E Lab Supervisor",
            role_value=supervisor_role_value,
        )
        pharmacy_role_value = _resolve_role_value("PHARMACY", "RECEPTION")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=pharmacy_email,
            password=pharmacy_password,
            full_name="E2E Pharmacy",
            role_value=pharmacy_role_value,
        )
        cmd_role_value = _resolve_role_value("CMD")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=cmd_email,
            password=cmd_password,
            full_name="E2E Chief Medical Director",
            role_value=cmd_role_value,
        )
        pharmacy_hod_role_value = _resolve_role_value("PHARMACY_HOD")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=pharmacy_hod_email,
            password=pharmacy_hod_password,
            full_name="E2E Pharmacy HOD",
            role_value=pharmacy_hod_role_value,
        )
        pharmacy_store_role_value = _resolve_role_value(
            "PHARMACY_STORE_OFFICER",
            "PHARMACY_HOD",
        )
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=pharmacy_store_email,
            password=pharmacy_store_password,
            full_name="E2E Pharmacy Store Officer",
            role_value=pharmacy_store_role_value,
        )
        cashier_role_value = _resolve_role_value("CASHIER", "RECEPTION")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=cashier_email,
            password=cashier_password,
            full_name="E2E Cashier",
            role_value=cashier_role_value,
        )
        clinic_admin_role_value = _resolve_role_value("CLINIC_ADMIN", "ADMIN")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=admin_email,
            password=admin_password,
            full_name="E2E Clinic Admin",
            role_value=clinic_admin_role_value,
        )

        db.commit()
        doctor_user = _get_user_by_email(db, doctor_email)
        lab_user = _get_user_by_email(db, lab_email)
        supervisor_user = _get_user_by_email(db, supervisor_email)
        pharmacist_user = _get_user_by_email(db, pharmacy_email)
        cmd_user = _get_user_by_email(db, cmd_email)
        store_user = _get_user_by_email(db, pharmacy_store_email)
        cashier_user = _get_user_by_email(db, cashier_email)
        _ensure_lab_workflow_seed(
            db,
            clinic=clinic,
            doctor=doctor_user,
            lab_user=lab_user,
            supervisor_user=supervisor_user,
            cashier_user=cashier_user,
        )
        _ensure_pharmacy_workflow_seed(
            db,
            clinic=clinic,
            pharmacist_user=pharmacist_user,
            cashier_user=cashier_user,
            doctor_user=doctor_user,
            patient_name=args.pharmacy_workflow_patient_name,
            phone_number=args.pharmacy_workflow_phone_number,
            batch_number=args.pharmacy_workflow_batch_number,
            stock_quantity=args.pharmacy_workflow_stock_quantity,
            prescribed_quantity=args.pharmacy_workflow_prescribed_quantity,
        )
        _ensure_return_to_store_seed(
            db,
            clinic=clinic,
            pharmacist_user=pharmacist_user,
            cmd_user=cmd_user,
            store_user=store_user,
            item_name=args.pharmacy_return_item_name,
            batch_number=args.pharmacy_return_batch_number,
            issued_quantity=args.pharmacy_return_issued_quantity,
        )
        print("Seeded Playwright users successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
