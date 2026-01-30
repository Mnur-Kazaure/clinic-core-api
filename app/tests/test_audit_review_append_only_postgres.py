import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

from app.models.clinic import Clinic
from app.models.user import User
from app.models.access_log import AccessLog
from app.models.event_log import EventLog
from app.models.audit_review_case import AuditReviewCase
from app.models.audit_review_item import AuditReviewItem
from app.models.audit_review_case_history import AuditReviewCaseHistory
from app.shared.enums import (
    UserRole,
    PurposeOfUse,
    AuditCaseSeverity,
    AuditCaseStatus,
    AuditItemType,
)


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_audit_review_append_only_enforced():
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
            full_name="Audit Admin",
            role=UserRole.CLINIC_ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()

        access_log = AccessLog(
            id=uuid.uuid4(),
            actor_id=admin.id,
            actor_role=admin.role,
            clinic_id=clinic.id,
            patient_id=None,
            action="SEARCH",
            purpose_of_use=PurposeOfUse.OPERATIONS,
            justification="legacy access log backfill",
            resource="SYSTEM",
            break_glass=False,
        )
        db.add(access_log)

        event_log = EventLog(
            id=uuid.uuid4(),
            event_type="ACCESS_LOGGED",
            actor_id=admin.id,
            actor_role=admin.role,
            clinic_id=clinic.id,
            patient_id=None,
            payload="{}",
        )
        db.add(event_log)

        case = AuditReviewCase(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            status=AuditCaseStatus.OPEN,
            severity=AuditCaseSeverity.LOW,
            reason="test",
            created_by=admin.id,
        )
        db.add(case)
        db.commit()

        item = AuditReviewItem(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            case_id=case.id,
            item_type=AuditItemType.ACCESS_LOG,
            access_log_id=access_log.id,
            event_log_id=None,
            added_by=admin.id,
            added_at=datetime.now(timezone.utc),
            notes=None,
        )
        db.add(item)
        db.commit()

        history = AuditReviewCaseHistory(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            case_id=case.id,
            from_status=None,
            to_status=AuditCaseStatus.OPEN,
            changed_by=admin.id,
            changed_at=datetime.now(timezone.utc),
            change_reason="created",
        )
        db.add(history)
        db.commit()

        item.notes = "updated"
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()

        db.delete(item)
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()

        history.change_reason = "updated"
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()

        db.delete(history)
        with pytest.raises(DBAPIError):
            db.commit()
    finally:
        db.close()
