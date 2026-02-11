import uuid
from datetime import date, datetime, timezone

from app.models.clinic import Clinic
from app.models.consultation import Consultation
from app.models.event_log import EventLog  # noqa: F401 (register model for sqlite create_all)
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.prescription_fulfillment_event import PrescriptionFulfillmentEvent  # noqa: F401
from app.models.user import User
from app.models.visit import Visit
from app.services.pharmacy_service import PharmacyService
from app.shared.enums import (
    Gender,
    PrescriptionStatus,
    RecordStatus,
    UserRole,
    VisitStatus,
)


def test_external_fulfillment_auto_completes_visit(db):
    clinic = Clinic(id=uuid.uuid4(), name="Clinic A")
    db.add(clinic)
    db.commit()

    doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email=f"doctor.{uuid.uuid4()}@example.com",
        password_hash="test",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    pharmacist = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email=f"pharmacy.{uuid.uuid4()}@example.com",
        password_hash="test",
        role=UserRole.PHARMACY,
        is_active=True,
    )
    db.add_all([doctor, pharmacist])
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        full_name="Patient A",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    db.add(patient)
    db.commit()

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.PHARMACY_PENDING,
        started_at=datetime.now(timezone.utc),
    )
    db.add(visit)
    db.commit()

    consultation = Consultation(
        id=uuid.uuid4(),
        visit_id=visit.id,
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        started_at=datetime.now(timezone.utc),
        record_status=RecordStatus.DRAFT,
    )
    db.add(consultation)
    db.commit()

    prescription = Prescription(
        id=uuid.uuid4(),
        consultation_id=consultation.id,
        visit_id=visit.id,
        clinic_id=clinic.id,
        prescribed_by=doctor.id,
        drug_name="Amoxicillin",
        dosage="500mg",
        frequency="Twice daily",
        duration="7 days",
        instructions="Take with food",
        status=PrescriptionStatus.ISSUED,
        record_status=RecordStatus.SIGNED,
        signed_at=datetime.now(timezone.utc),
        issued_at=datetime.now(timezone.utc),
    )
    db.add(prescription)
    db.commit()

    PharmacyService(db).mark_dispensed_external(
        prescription,
        actor_id=pharmacist.id,
        note="Out of stock; patient to buy outside",
    )

    updated = db.query(Visit).filter(Visit.id == visit.id).first()
    assert updated is not None
    assert updated.status == VisitStatus.COMPLETED
