import uuid
from datetime import date, datetime, timezone

from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.patient_identity_map import PatientIdentityMap
from app.models.identity_map_revocation import IdentityMapRevocation
from app.models.identity_case import IdentityCase
from app.services.pmr_service import PMRService
from app.shared.enums import Gender, UserRole, IdentityCaseType, IdentityCaseStatus


def test_pmr_identity_closure_respects_revocations(db, clinic_id):
    clinic = Clinic(id=clinic_id, name="Clinic A")
    db.add(clinic)
    db.commit()

    admin = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"admin.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Admin",
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
    db.add_all([patient_a, patient_b])
    db.commit()

    mapping = PatientIdentityMap(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        from_patient_id=patient_a.id,
        to_patient_id=patient_b.id,
        mapped_at=datetime.now(timezone.utc),
        mapped_by=admin.id,
    )
    db.add(mapping)
    db.commit()

    case = IdentityCase(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        case_type=IdentityCaseType.MERGE,
        status=IdentityCaseStatus.APPROVED,
        created_by=admin.id,
        created_at=datetime.now(timezone.utc),
        reason="duplicate",
        primary_patient_id=patient_a.id,
        target_patient_id=patient_b.id,
    )
    db.add(case)
    db.commit()

    revocation = IdentityMapRevocation(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        map_id=mapping.id,
        case_id=case.id,
        revoked_by=admin.id,
        revoked_at=datetime.now(timezone.utc),
        reason="rollback",
    )
    db.add(revocation)
    db.commit()

    service = PMRService(db)
    closure = service._resolve_identity_closure(
        canonical_id=patient_b.id,
        clinic_id=clinic_id,
    )
    assert patient_a.id not in closure
    assert patient_b.id in closure
