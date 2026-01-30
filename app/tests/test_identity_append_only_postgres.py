import os
import uuid
import pytest
from datetime import datetime, timezone, date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.identity_case import IdentityCase
from app.models.identity_evidence import IdentityEvidence
from app.models.identity_approval import IdentityApproval
from app.models.patient_alias import PatientAlias
from app.models.patient_identity_map import PatientIdentityMap
from app.models.identity_map_revocation import IdentityMapRevocation
from app.shared.enums import (
    Gender,
    IdentityCaseType,
    IdentityCaseStatus,
    IdentityEvidenceType,
    IdentityApprovalRole,
    IdentityApprovalDecision,
    PatientAliasType,
    PatientAliasConfidence,
    PatientAliasSource,
)


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_identity_append_only_enforced():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    alembic_cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", POSTGRES_TEST_URL)
    original_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = POSTGRES_TEST_URL
    try:
        command.upgrade(alembic_cfg, "head")
    finally:
        if original_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_database_url

    db = SessionLocal()
    try:
        clinic = Clinic(id=uuid.uuid4(), name="Clinic A")
        db.add(clinic)
        db.commit()

        admin = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"admin.{uuid.uuid4()}@example.com",
            password_hash="test",
            full_name="Admin",
            role="ADMIN",
            is_active=True,
        )
        db.add(admin)
        db.commit()

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name="Alias Patient",
            date_of_birth=date(2000, 1, 1),
            gender=Gender.MALE,
            phone_number="000",
            address="Test",
            occupation="Test",
        )
        db.add(patient)
        db.commit()

        case = IdentityCase(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            case_type=IdentityCaseType.MERGE,
            status=IdentityCaseStatus.OPEN,
            created_by=admin.id,
            reason="duplicate record",
            primary_patient_id=patient.id,
        )
        db.add(case)
        db.commit()

        alias = PatientAlias(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            patient_id=patient.id,
            alias_type=PatientAliasType.NAME,
            value="Alias Name",
            confidence=PatientAliasConfidence.HIGH,
            source=PatientAliasSource.STAFF,
            captured_by=admin.id,
            captured_at=datetime.now(timezone.utc),
        )
        db.add(alias)
        db.commit()

        evidence = IdentityEvidence(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            case_id=case.id,
            evidence_type=IdentityEvidenceType.DOCUMENT_REF,
            ref="doc-1",
            notes=None,
            added_by=admin.id,
            added_at=datetime.now(timezone.utc),
        )
        db.add(evidence)
        db.commit()

        approval = IdentityApproval(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            case_id=case.id,
            approver_role=IdentityApprovalRole.ADMIN,
            approver_id=admin.id,
            decision=IdentityApprovalDecision.APPROVE,
            decision_reason="approved",
            decided_at=datetime.now(timezone.utc),
        )
        db.add(approval)
        db.commit()

        mapping = PatientIdentityMap(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            from_patient_id=patient.id,
            to_patient_id=patient.id,
            mapped_at=datetime.now(timezone.utc),
            mapped_by=admin.id,
        )
        db.add(mapping)
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()

        # create valid map for revocation test
        patient_b = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name="Alias Patient B",
            date_of_birth=date(2000, 1, 1),
            gender=Gender.MALE,
            phone_number="000",
            address="Test",
            occupation="Test",
        )
        db.add(patient_b)
        db.commit()

        mapping = PatientIdentityMap(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            from_patient_id=patient.id,
            to_patient_id=patient_b.id,
            mapped_at=datetime.now(timezone.utc),
            mapped_by=admin.id,
        )
        db.add(mapping)
        db.commit()

        revocation = IdentityMapRevocation(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            map_id=mapping.id,
            case_id=case.id,
            revoked_by=admin.id,
            revoked_at=datetime.now(timezone.utc),
            reason="mistake",
        )
        db.add(revocation)
        db.commit()

        alias.value = "Updated"
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()

        db.delete(evidence)
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()

        db.delete(approval)
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()

        db.delete(revocation)
        with pytest.raises(DBAPIError):
            db.commit()
    finally:
        db.close()
