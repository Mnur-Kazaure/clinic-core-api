from uuid import UUID
from app.core.database import SessionLocal
from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient

db = SessionLocal()

clinic_id = UUID("22222222-2222-2222-2222-222222222222")

db.add(Clinic(
    id=clinic_id,
    name="Demo Clinic"
))

db.commit()
db.close()