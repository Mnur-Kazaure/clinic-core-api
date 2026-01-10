# app/api/v1/router.py
from fastapi import APIRouter
from . import auth, patient, visit, consultation, lab, pharmacy, lab_request, prescriptions

# app/api/v1/router.py
api_router = APIRouter(prefix="/api")


api_router.include_router(visit.router, tags=["visits"])
# api_router.include_router(consultation.router, tags=["consultations"])
api_router.include_router(lab.router, tags=["lab"])
api_router.include_router(pharmacy.router, tags=["pharmacy"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(patient.router, tags=["patient"])
api_router.include_router(consultation.router, tags=["consultations"])
api_router.include_router(lab_request.router, tags=["lab_requests"])
api_router.include_router(prescriptions.router, tags=["prescriptions"])