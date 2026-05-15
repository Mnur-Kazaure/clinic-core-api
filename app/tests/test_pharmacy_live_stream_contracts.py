import json
import uuid

from app.api.v1._sse import encode_sse_event
from app.api.v1.billing import get_cashier_dashboard
from app.api.v1.pharmacy import get_dispensing_dashboard
from app.api.v1.pharmacy_hod import get_pharmacy_hod_dashboard
from app.api.v1.pharmacy_store import get_store_dashboard
from app.models.pharmacy_unit_profile import PharmacyUnitProfile
from app.models.service_line import ServiceLine
from app.models.user import User
from app.services.billing_workflow_service import BillingWorkflowService
from app.services.cashier_pay_point_access_service import CashierPayPointAccessService
from app.services.pharmacy_supply_service import PharmacySupplyService
from app.services.pharmacy_unit_access_service import PharmacyUnitAccessService
from app.services.prescription_service import PrescriptionService
from app.shared.enums import BillingReasonCode, PharmacyUnitCategory, UserRole
from app.tests.test_pharmacy_enterprise_workflow import _seed_core_context


def _add_hod_user(db, clinic_id):
    hod = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email="pharmacy.hod.stream@test.example",
        password_hash="x",
        full_name="Pharmacy HOD",
        role=UserRole.PHARMACY_HOD.value,
        is_active=True,
    )
    db.add(hod)
    db.commit()
    return hod


def _add_store_officer_user(db, clinic_id):
    store_officer = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email="pharmacy.store.stream@test.example",
        password_hash="x",
        full_name="Pharmacy Store Officer",
        role=UserRole.PHARMACY_STORE_OFFICER.value,
        is_active=True,
    )
    db.add(store_officer)
    db.commit()
    return store_officer


def _get_store_unit(db, clinic_id):
    return (
        db.query(ServiceLine)
        .join(PharmacyUnitProfile, PharmacyUnitProfile.service_line_id == ServiceLine.id)
        .filter(
            ServiceLine.clinic_id == clinic_id,
            PharmacyUnitProfile.unit_category == PharmacyUnitCategory.STORE,
        )
        .first()
    )


def test_pharmacy_live_stream_encoder_formats_snapshot_payload():
    encoded = encode_sse_event(
        event="pharmacy_dashboard_snapshot",
        data={"overview": {"ready_to_dispense": 1}},
        event_id="2026-03-24T12:00:00+00:00",
    )

    assert "event: pharmacy_dashboard_snapshot" in encoded
    assert "id: 2026-03-24T12:00:00+00:00" in encoded

    data_line = next(line for line in encoded.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload["overview"]["ready_to_dispense"] == 1


def test_pharmacy_live_dashboard_handlers_return_scoped_snapshots(db, clinic_id):
    ctx = _seed_core_context(db, clinic_id)
    hod = _add_hod_user(db, ctx["clinic"].id)
    store_officer = _add_store_officer_user(db, ctx["clinic"].id)
    store_unit = _get_store_unit(db, ctx["clinic"].id)
    assert store_unit is not None

    PharmacyUnitAccessService(db).sync_user_units(
        clinic_id=ctx["clinic"].id,
        user=ctx["pharmacist"],
        role=UserRole.PHARMACY,
        allowed_unit_ids=[ctx["adult_unit"].id],
        default_unit_id=ctx["adult_unit"].id,
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
    prescription = PrescriptionService(db).issue_prescription(
        consultation=ctx["consultation"],
        visit_id=ctx["visit"].id,
        doctor_id=ctx["doctor"].id,
        payload=type(
            "Payload",
            (),
            {
                "drug_name": "Paracetamol",
                "dosage": "1 tab",
                "frequency": "bd",
                "duration": "5 days",
                "instructions": None,
            },
        )(),
    )
    BillingWorkflowService(db).pay_billing_items(
        clinic_id=ctx["clinic"].id,
        visit_id=ctx["visit"].id,
        billing_item_ids=[prescription.billing_item_id],
        cashier_pay_point_id=ctx["pharmacy_pay_point"].id,
        payment_method=BillingReasonCode.CASH,
        cashier_user=ctx["cashier"],
        notes="Medication payment",
    )
    PharmacySupplyService(db).create_refill_request(
        clinic_id=ctx["clinic"].id,
        actor=ctx["pharmacist"],
        payload=type(
            "RefillPayload",
            (),
            {
                "unit_id": ctx["adult_unit"].id,
                "urgency": "HIGH",
                "note": "Need replenishment",
                "items": [
                    type(
                        "RefillItem",
                        (),
                        {
                            "inventory_item_id": ctx["inventory_item"].id,
                            "requested_quantity": 5,
                            "note": None,
                        },
                    )()
                ],
            },
        )(),
    )

    cashier_dashboard = get_cashier_dashboard(
        cashier_pay_point_id=ctx["pharmacy_pay_point"].id,
        search=None,
        limit=50,
        db=db,
        current_user=ctx["cashier"],
    )
    pharmacy_dashboard = get_dispensing_dashboard(
        unit_id=ctx["adult_unit"].id,
        db=db,
        current_user=ctx["pharmacist"],
    )
    hod_dashboard = get_pharmacy_hod_dashboard(
        start_date=None,
        end_date=None,
        db=db,
        current_user=hod,
    )
    store_dashboard = get_store_dashboard(
        start_date=None,
        end_date=None,
        store_unit_id=store_unit.id,
        db=db,
        current_user=store_officer,
    )

    assert cashier_dashboard["overview"]["pharmacy_charges_pending"] == 0
    assert pharmacy_dashboard.unit_id == ctx["adult_unit"].id
    assert pharmacy_dashboard.overview.ready_to_dispense == 1
    assert hod_dashboard.overview.ready_to_dispense == 1
    assert store_dashboard.store_unit_id == store_unit.id
