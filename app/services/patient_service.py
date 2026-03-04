# app/services/patient_service.py
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.patient_mrn import PatientMRN
from app.schemas.patient import PatientCreateSchema
from app.shared.enums import IdentityState, MRNStatus
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

        patients = (
            query.order_by(Patient.full_name.asc())
            .limit(limit)
            .all()
        )
        self._attach_active_mrns(clinic_id=clinic_id, patients=patients)
        return patients

    def list_patients(
        self,
        *,
        clinic_id,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ):
        query = self.db.query(Patient).filter(Patient.clinic_id == clinic_id)

        if q:
            pattern = f"%{q}%"
            query = query.filter(
                or_(
                    Patient.full_name.ilike(pattern),
                    Patient.phone_number.ilike(pattern),
                    Patient.address.ilike(pattern),
                    Patient.occupation.ilike(pattern),
                )
            )

        total = query.count()
        patients = (
            query.order_by(Patient.created_at.desc(), Patient.full_name.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        self._attach_active_mrns(clinic_id=clinic_id, patients=patients)

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": patients,
        }

    def get_patient(self, *, clinic_id, patient_id):
        patient = (
            self.db.query(Patient)
            .filter(
                Patient.id == patient_id,
                Patient.clinic_id == clinic_id,
            )
            .first()
        )
        if patient is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found",
            )
        self._attach_active_mrns(clinic_id=clinic_id, patients=[patient])
        return patient

    def _attach_active_mrns(self, *, clinic_id, patients: list[Patient]) -> None:
        if not patients:
            return

        patient_ids = [patient.id for patient in patients]
        mrn_rows = (
            self.db.query(PatientMRN.patient_id, PatientMRN.mrn)
            .filter(
                PatientMRN.clinic_id == clinic_id,
                PatientMRN.patient_id.in_(patient_ids),
                PatientMRN.status == MRNStatus.ACTIVE,
            )
            .order_by(
                PatientMRN.patient_id.asc(),
                PatientMRN.issued_at.desc(),
            )
            .all()
        )

        mrn_map: dict = {}
        for patient_id, mrn in mrn_rows:
            if patient_id not in mrn_map:
                mrn_map[patient_id] = mrn

        for patient in patients:
            patient.patient_mrn = mrn_map.get(patient.id)




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
