# app/services/patient_service.py
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.clinic import Clinic
from app.models.patient import Patient
from app.schemas.patient import PatientCreateSchema
from app.shared.enums import IdentityState
from app.services.mrn_service import MRNService


class PatientService:
    def __init__(self, db: Session):
        self.db = db

    def create_patient(self, payload: PatientCreateSchema, current_user):
        """
        Create a patient under the same clinic.

        Authorization is enforced at the API boundary (router dependency).
        Service assumes caller is already authorized.
        """

        clinic = (
            self.db.query(Clinic)
            .filter(Clinic.id == current_user.clinic_id)
            .first()
        )
        if not clinic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clinic not found",
            )

        # Registration payments are temporarily disabled until the clinic's payment workflow
        # is finalized. Patient creation must not be blocked by fee configuration.

        patient = Patient(
            clinic_id=current_user.clinic_id,
            full_name=payload.full_name,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            phone_number=payload.phone_number,
            address=payload.address,
            occupation=payload.occupation,
            identity_state=payload.identity_state or IdentityState.VERIFIED,
            created_reason=payload.created_reason,
        )

        self.db.add(patient)
        try:
            self.db.flush()
            mrn = MRNService(self.db).issue_mrn_for_patient(
                patient_id=patient.id,
                clinic_id=current_user.clinic_id,
                actor=current_user,
                commit=False,
            )

            self.db.commit()
            self.db.refresh(patient)
            patient.patient_mrn = mrn.mrn
        except Exception:
            self.db.rollback()
            raise

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
