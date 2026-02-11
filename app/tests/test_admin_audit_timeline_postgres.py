import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.admin import get_audit_timeline
from app.models.access_log import AccessLog
from app.models.clinic import Clinic
from app.models.event_log import EventLog
from app.models.user import User
from app.shared.enums import PurposeOfUse, UserRole


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_admin_audit_timeline_includes_access_and_events():
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
        clinic = Clinic(id=uuid.uuid4(), name="Clinic A", billing_currency="NGN")
        db.add(clinic)
        db.commit()

        admin = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"admin_{clinic.id}@example.test",
            password_hash="test",
            full_name="Admin User",
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
            action="ACCESS_LOGGED",
            purpose_of_use=PurposeOfUse.OPERATIONS,
            justification="Admin audit view",
            resource="PMR",
            break_glass=False,
        )
        db.add(access_log)

        event_log = EventLog(
            id=uuid.uuid4(),
            event_type="BREAK_GLASS_USED",
            actor_id=admin.id,
            actor_role=admin.role,
            clinic_id=clinic.id,
            patient_id=None,
            payload="{}",
        )
        db.add(event_log)
        db.commit()

        items = get_audit_timeline(
            db=db,
            current_user=admin,
            limit=50,
            from_dt=None,
            to_dt=None,
            event_type=None,
            actor_id=None,
        )

        assert len(items) >= 2
        sources = {item.source for item in items}
        assert "EVENT" in sources
        assert "ACCESS" in sources
    finally:
        db.close()
