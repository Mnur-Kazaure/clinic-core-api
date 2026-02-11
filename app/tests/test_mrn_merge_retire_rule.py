import uuid
from datetime import date

from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.patient_mrn import PatientMRN
from app.services.identity_service import IdentityService
from app.services.mrn_service import MRNService
from app.schemas.identity import (
    IdentityCaseCreateRequest,
    IdentityEvidenceCreateRequest,
    IdentityApprovalRequest,
)
from app.shared.enums import (
    Gender,
    UserRole,
    IdentityCaseType,
    IdentityEvidenceType,
    IdentityApprovalDecision,
    MRNStatus,
)


def test_merge_retires_non_canonical_mrn(db, clinic_id):
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
    clinic_admin = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"cadmin.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Clinic Admin",
        role=UserRole.CLINIC_ADMIN,
        is_active=True,
    )
    db.add_all([admin, clinic_admin])
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

    mrn_service = MRNService(db)
    mrn_service.issue_mrn_for_patient(
        patient_id=patient_a.id,
        clinic_id=clinic_id,
        actor=admin,
    )
    mrn_service.issue_mrn_for_patient(
        patient_id=patient_b.id,
        clinic_id=clinic_id,
        actor=admin,
    )

    service = IdentityService(db)
    case = service.create_case(
        payload=IdentityCaseCreateRequest(
            case_type=IdentityCaseType.MERGE,
            primary_patient_id=patient_a.id,
            target_patient_id=patient_b.id,
            reason="duplicate",
        ),
        current_user=admin,
    )
    service.add_evidence(
        case_id=case.id,
        payload=IdentityEvidenceCreateRequest(
            evidence_type=IdentityEvidenceType.DOCUMENT_REF,
            ref="doc-1",
            notes=None,
        ),
        current_user=admin,
    )
    service.add_evidence(
        case_id=case.id,
        payload=IdentityEvidenceCreateRequest(
            evidence_type=IdentityEvidenceType.STAFF_WITNESS,
            ref="witness-1",
            notes=None,
        ),
        current_user=admin,
    )
    service.approve_case(
        case_id=case.id,
        payload=IdentityApprovalRequest(
            decision=IdentityApprovalDecision.APPROVE,
            decision_reason="approved",
        ),
        current_user=admin,
    )
    service.approve_case(
        case_id=case.id,
        payload=IdentityApprovalRequest(
            decision=IdentityApprovalDecision.APPROVE,
            decision_reason="approved",
        ),
        current_user=clinic_admin,
    )
    service.apply_case(case_id=case.id, current_user=admin)

    mrns_a = (
        db.query(PatientMRN)
        .filter(
            PatientMRN.clinic_id == clinic_id,
            PatientMRN.patient_id == patient_a.id,
        )
        .all()
    )
    assert mrns_a
    assert all(mrn.status == MRNStatus.RETIRED for mrn in mrns_a)

    active_b = (
        db.query(PatientMRN)
        .filter(
            PatientMRN.clinic_id == clinic_id,
            PatientMRN.patient_id == patient_b.id,
            PatientMRN.status == MRNStatus.ACTIVE,
        )
        .first()
    )
    assert active_b is not None
