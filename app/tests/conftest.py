import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.models.base import Base
from app.shared.enums import UserRole, VisitStatus
from app.models.user import User
from app.models.visit import Visit
import uuid


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def clinic_id():
    return uuid.uuid4()


@pytest.fixture
def receptionist(db, clinic_id):
    user = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"reception_{clinic_id}@example.test",
        password_hash="test",
        role=UserRole.RECEPTION,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def doctor(db, clinic_id):
    user = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"doctor_{clinic_id}@example.test",
        password_hash="test",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def chew(db, clinic_id):
    user = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"chew_{clinic_id}@example.test",
        password_hash="test",
        role=UserRole.CHEW,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def midwife(db, clinic_id):
    user = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"midwife_{clinic_id}@example.test",
        password_hash="test",
        role=UserRole.MIDWIFE,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def visit_registered(db, clinic_id, doctor):
    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=uuid.uuid4(),
        assigned_doctor_id=doctor.id,
        status=VisitStatus.REGISTERED,
    )
    db.add(visit)
    db.commit()
    return visit
