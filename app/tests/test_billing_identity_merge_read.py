import uuid
from datetime import date, datetime, timezone

from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.visit import Visit
from app.models.patient_identity_map import PatientIdentityMap
from app.models.billing_ledger_entry import BillingLedgerEntry
from app.services.billing_service import BillingService
from app.shared.enums import (
    Gender,
    UserRole,
    VisitStatus,
    BillingEntryType,
    BillingReasonCode,
)


def test_billing_identity_merge_read_transitive(db, clinic_id):
    clinic = Clinic(id=clinic_id, name="Clinic A", billing_currency="NGN")
    db.add(clinic)
    db.commit()

    admin = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"admin.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Billing Admin",
        role=UserRole.CLINIC_ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()

    patient_a = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Patient A",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    patient_b = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Patient B",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    patient_c = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Patient C",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    db.add_all([patient_a, patient_b, patient_c])
    db.commit()

    visit_a = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_a.id,
        assigned_doctor_id=admin.id,
        status=VisitStatus.IN_CONSULTATION,
    )
    visit_b = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_b.id,
        assigned_doctor_id=admin.id,
        status=VisitStatus.IN_CONSULTATION,
    )
    db.add_all([visit_a, visit_b])
    db.commit()

    entry_a = BillingLedgerEntry(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_a.id,
        visit_id=visit_a.id,
        admission_id=None,
        entry_type=BillingEntryType.CHARGE,
        amount_minor=1000,
        currency="NGN",
        description="Charge A",
        reason_code=BillingReasonCode.SERVICE,
        external_ref=None,
        related_entry_id=None,
        actor_id=admin.id,
        actor_role=admin.role,
        occurred_at=datetime.now(timezone.utc),
    )
    entry_b = BillingLedgerEntry(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_b.id,
        visit_id=visit_b.id,
        admission_id=None,
        entry_type=BillingEntryType.CHARGE,
        amount_minor=2000,
        currency="NGN",
        description="Charge B",
        reason_code=BillingReasonCode.SERVICE,
        external_ref=None,
        related_entry_id=None,
        actor_id=admin.id,
        actor_role=admin.role,
        occurred_at=datetime.now(timezone.utc),
    )
    db.add_all([entry_a, entry_b])
    db.commit()

    map_ab = PatientIdentityMap(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        from_patient_id=patient_a.id,
        to_patient_id=patient_b.id,
        mapped_at=datetime.now(timezone.utc),
        mapped_by=admin.id,
    )
    map_bc = PatientIdentityMap(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        from_patient_id=patient_b.id,
        to_patient_id=patient_c.id,
        mapped_at=datetime.now(timezone.utc),
        mapped_by=admin.id,
    )
    db.add_all([map_ab, map_bc])
    db.commit()

    service = BillingService(db)
    entries_for_a = service.get_ledger_for_patient(
        patient_id=patient_a.id,
        clinic_id=clinic_id,
    )
    entries_for_c = service.get_ledger_for_patient(
        patient_id=patient_c.id,
        clinic_id=clinic_id,
    )

    assert len(entries_for_a) == 2
    assert len(entries_for_c) == 2
    assert {entry.patient_id for entry in entries_for_a} == {patient_a.id, patient_b.id}
