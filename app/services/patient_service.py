# app/services/patient_service.py
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.schemas.patient import PatientCreateSchema


class PatientService:
    def __init__(self, db: Session):
        self.db = db

    def create_patient(self, payload: PatientCreateSchema, current_user):
        """
        Create a patient under the same clinic.

        Authorization is enforced at the API boundary (router dependency).
        Service assumes caller is already authorized.
        """

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

    def search_patients(
        self,
        *,
        clinic_id,
        q: str | None = None,
        full_name: str | None = None,
        phone_number: str | None = None,
        limit: int = 20,
    ):
        if not q and not full_name and not phone_number:
            raise ValueError("Search term required")

        query = self.db.query(Patient).filter(Patient.clinic_id == clinic_id)

        if q:
            pattern = f"%{q}%"
            query = query.filter(
                or_(
                    Patient.full_name.ilike(pattern),
                    Patient.phone_number.ilike(pattern),
                )
            )

        if full_name:
            query = query.filter(Patient.full_name.ilike(f"%{full_name}%"))

        if phone_number:
            query = query.filter(Patient.phone_number.ilike(f"%{phone_number}%"))

        return (
            query.order_by(Patient.full_name.asc())
            .limit(limit)
            .all()
        )




# # app/services/patient_service.py
# from sqlalchemy.orm import Session

# from app.models.patient import Patient
# from app.schemas.patient import PatientCreateSchema
# from app.core.guards.patient_guards import require_reception_role


# class PatientService:
#     def __init__(self, db: Session):
#         self.db = db

#     def create_patient(self, payload: PatientCreateSchema, current_user):
#         """
#         Create a patient under the same clinic.
#         Only Reception role is permitted.
#         """
#         require_reception_role(current_user)

#         patient = Patient(
#             clinic_id=current_user.clinic_id,
#             full_name=payload.full_name,
#             date_of_birth=payload.date_of_birth,
#             gender=payload.gender,
#             phone_number=payload.phone_number,
#             address=payload.address,
#             occupation=payload.occupation,
#         )

#         self.db.add(patient)
#         self.db.commit()
#         self.db.refresh(patient)

#         return patient
