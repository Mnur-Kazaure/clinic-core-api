from __future__ import annotations
# app/api/v1/cmd_oversight.py - CMD Executive API Routes

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.shared.enums import UserRole
from app.schemas.cmd_oversight import ExecutiveStatsResponse, ActivityFeedItem, StaffPerformanceItem, PatientProfileResponse
from app.schemas.patient import PatientReadSchema
from app.services.cmd_oversight_service import CMDOversightService
from typing import List
from uuid import UUID

router = APIRouter(prefix="/cmd", tags=["cmd"])

def require_cmd_role(user = Depends(get_current_user)):
    if user.role != UserRole.CMD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CMD authority required"
        )
    return user

@router.get("/stats", response_model=ExecutiveStatsResponse)
def get_cmd_stats(
    db: Session = Depends(get_db),
    current_user = Depends(require_cmd_role)
):
    return CMDOversightService(db).get_executive_stats(current_user.clinic_id)

@router.get("/activity", response_model=List[ActivityFeedItem])
def get_cmd_activity(
    db: Session = Depends(get_db),
    current_user = Depends(require_cmd_role)
):
    return CMDOversightService(db).get_live_activity(current_user.clinic_id)

@router.get("/performance", response_model=List[StaffPerformanceItem])
def get_staff_performance(
    db: Session = Depends(get_db),
    current_user = Depends(require_cmd_role)
):
    return CMDOversightService(db).get_staff_performance(current_user.clinic_id)

@router.get("/wards")
def get_ward_occupancy(
    db: Session = Depends(get_db),
    current_user = Depends(require_cmd_role)
):
    return CMDOversightService(db).get_ward_occupancy(current_user.clinic_id)

@router.get("/patient/{patient_id}", response_model=PatientProfileResponse)
def get_patient_profile(
    patient_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(require_cmd_role)
):
    profile = CMDOversightService(db).get_patient_profile(current_user.clinic_id, patient_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Patient not found")
    return profile

@router.get("/search/patients", response_model=List[PatientReadSchema])
def search_patients(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user = Depends(require_cmd_role)
):
    return CMDOversightService(db).search_patients(current_user.clinic_id, q)
