from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.schemas.patient import PatientCreateSchema
from app.core.guards.patient_guards import require_reception_role


class PatientService:
    def __init__(self, db: Session):
        self.db = db

    def create_patient(self, payload: PatientCreateSchema, current_user):
        """
        Create a patient under the same clinic.
        Only Reception role is permitted.
        """
        require_reception_role(current_user)

        patient = Patient(
            clinic_id=current_user.clinic_id,
            full_name=payload.full_name,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            phone_number=payload.phone_number,
            address=payload.address,
            occupation=payload.occupation,
        )

        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)

        return patient