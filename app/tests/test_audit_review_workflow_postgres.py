import os
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

from app.models.clinic import Clinic
from app.models.user import User
from app.models.audit_review_case_history import AuditReviewCaseHistory
from app.services.audit_review_service import AuditReviewService
from app.schemas.audit_review import (
    AuditReviewCaseCreateRequest,
    AuditReviewCaseStartRequest,
    AuditReviewCaseCloseRequest,
)
from app.shared.enums import AuditCaseSeverity, AuditCaseOutcome, UserRole


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_audit_review_workflow():
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
            full_name="Workflow Admin",
            role=UserRole.CLINIC_ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()

        service = AuditReviewService(db)
        case = service.create_case(
            payload=AuditReviewCaseCreateRequest(
                severity=AuditCaseSeverity.HIGH,
                reason="Suspicious access",
            ),
            current_user=admin,
        )
        assert case.status.name == "OPEN"

        case = service.start_review(
            case_id=case.id,
            payload=AuditReviewCaseStartRequest(reason="triage"),
            current_user=admin,
        )
        assert case.status.name == "IN_REVIEW"
        assert case.reviewed_by == admin.id

        case = service.close_case(
            case_id=case.id,
            payload=AuditReviewCaseCloseRequest(
                outcome=AuditCaseOutcome.JUSTIFIED,
                reason="resolved",
            ),
            current_user=admin,
        )
        assert case.status.name == "CLOSED"
        assert case.closed_by == admin.id
        assert case.closed_at is not None

        history = db.query(AuditReviewCaseHistory).filter(AuditReviewCaseHistory.case_id == case.id).all()
        assert len(history) == 2
    finally:
        db.close()
