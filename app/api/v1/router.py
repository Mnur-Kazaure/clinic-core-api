# app/api/v1/router.py
from fastapi import APIRouter
from . import auth, patient, visit, consultation, lab, pharmacy

# app/api/v1/router.py
api_router = APIRouter(prefix="/api")


api_router.include_router(visit.router, tags=["visits"])
# api_router.include_router(consultation.router, tags=["consultations"])
api_router.include_router(lab.router, tags=["lab"])
api_router.include_router(pharmacy.router, tags=["pharmacy"])
api_router.include_router(auth.router, tags=["auth"])



# from fastapi import APIRouter

# from app.api.v1 import (
#     auth,
#     patient,
#     visit,
#     consultation,
#     lab,
#     pharmacy,
# )



# api_router.include_router(auth.router)
# api_router.include_router(patient.router)
# api_router.include_router(visit.router)
# api_router.include_router(consultation.router)
# api_router.include_router(lab.router)
# api_router.include_router(pharmacy.router)
