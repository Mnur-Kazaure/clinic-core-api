# app/api/v1/router.py
from fastapi import APIRouter
from . import auth, patient, visit, consultation, lab, pharmacy, lab_request, prescriptions, clinic_registration, clinic_profile, clinic_staff, user, doctor_lab, admissions, beds, wards, priority, identity, audit_review

# app/api/v1/router.py
api_router = APIRouter(prefix="/api/v1")


api_router.include_router(visit.router, tags=["visits"])
# api_router.include_router(consultation.router, tags=["consultations"])
api_router.include_router(lab.router, tags=["lab"])
api_router.include_router(pharmacy.router, tags=["pharmacy"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(patient.router, tags=["patient"])
api_router.include_router(consultation.router, tags=["consultations"])
api_router.include_router(doctor_lab.router, tags=["doctor"])
api_router.include_router(lab_request.router, tags=["lab_requests"])
api_router.include_router(prescriptions.router, tags=["prescriptions"])
api_router.include_router(clinic_registration.router, tags=["clinic"])
api_router.include_router(clinic_profile.router, tags=["clinic"])
api_router.include_router(clinic_staff.router, tags=["clinic"])
api_router.include_router(user.router, tags=["users"])
api_router.include_router(admissions.router, tags=["admissions"])
api_router.include_router(beds.router, tags=["beds"])
api_router.include_router(wards.router, tags=["wards"])
api_router.include_router(priority.router, tags=["priority"])
api_router.include_router(identity.router, tags=["identity"])
api_router.include_router(audit_review.router, tags=["audit_review"])
