# app/api/v1/router.py
from fastapi import APIRouter
from . import (
    admin,
    admissions,
    anc,
    attendance,
    cmd_oversight,
    audit_review,
    auth,
    bed_board,
    beds,
    billing,
    chronic_recalls,
    clinic_profile,
    clinic_registration,
    clinic_staff,
    condition_profiles,
    consultation,
    diagnosis_mappings,
    doctor_lab,
    follow_ups,
    identity,
    lab,
    lab_request,
    maternity,
    patient,
    pharmacy,
    pmr,
    prescriptions,
    priority,
    user,
    visit,
    wards,
)

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
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(user.router, tags=["users"])
api_router.include_router(admissions.router, tags=["admissions"])
api_router.include_router(beds.router, tags=["beds"])
api_router.include_router(wards.router, tags=["wards"])
api_router.include_router(bed_board.router, tags=["bed_board"])
api_router.include_router(priority.router, tags=["priority"])
api_router.include_router(identity.router, tags=["identity"])
api_router.include_router(audit_review.router, tags=["audit_review"])
api_router.include_router(billing.router, tags=["billing"])
api_router.include_router(pmr.router, tags=["pmr"])
api_router.include_router(anc.router, tags=["anc"])
api_router.include_router(maternity.router, tags=["maternity"])
api_router.include_router(condition_profiles.router, tags=["condition_profiles"])
api_router.include_router(diagnosis_mappings.router, tags=["diagnosis_mappings"])
api_router.include_router(chronic_recalls.router, tags=["chronic_recalls"])
api_router.include_router(follow_ups.router, tags=["follow_ups"])
api_router.include_router(attendance.router, tags=["attendance"])
api_router.include_router(cmd_oversight.router, tags=["cmd"])
