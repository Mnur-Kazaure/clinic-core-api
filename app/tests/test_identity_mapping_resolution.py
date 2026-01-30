import uuid
from datetime import date, timezone, datetime

from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.patient_identity_map import PatientIdentityMap
from app.services.identity_service import IdentityService
from app.shared.enums import Gender, UserRole


def test_identity_mapping_resolves_multi_hop(db, clinic_id):
    clinic = Clinic(id=clinic_id, name="Clinic A")
    db.add(clinic)
    db.commit()

    admin = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"admin.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Admin",
        role=UserRole.ADMIN,
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

    service = IdentityService(db)
    resolved = service.resolve_canonical_patient_id(
        patient_id=patient_a.id,
        clinic_id=clinic_id,
    )
    assert resolved == patient_c.id
