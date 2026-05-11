import uuid

from fastapi import Response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.consultation import start_consultation
import app.models  # noqa: F401
from app.models.base import Base
from app.models.user import User
from app.models.visit import Visit
from app.shared.enums import UserRole, VisitStatus
from app.schemas.consultation import ConsultationCreateRequest


def _make_test_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_start_consultation_is_idempotent():
    engine = _make_test_engine()
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        clinic_id = uuid.uuid4()
        doctor = User(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            email=f"doctor_{clinic_id}@example.test",
            password_hash="test",
            role=UserRole.DOCTOR,
            is_active=True,
        )
        visit = Visit(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            patient_id=uuid.uuid4(),
            assigned_doctor_id=doctor.id,
            status=VisitStatus.IN_CONSULTATION,
        )
        db.add_all([doctor, visit])
        db.commit()

        payload = ConsultationCreateRequest(visit_id=visit.id)

        response_first = Response()
        consultation_first = start_consultation(
            payload=payload,
            response=response_first,
            db=db,
            current_user=doctor,
        )
        assert response_first.status_code == 201
        assert consultation_first.id

        response_second = Response()
        consultation_second = start_consultation(
            payload=payload,
            response=response_second,
            db=db,
            current_user=doctor,
        )
        assert response_second.status_code == 200
        assert consultation_second.id == consultation_first.id
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
