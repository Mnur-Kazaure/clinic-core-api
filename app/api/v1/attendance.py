# app/api/v1/attendance.py

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.rbac import require_clinic_admin
from app.schemas.attendance import AttendancePunchRequest, AttendanceLogResponse
from app.services.attendance_service import AttendanceService
from typing import List

router = APIRouter(prefix="/attendance", tags=["attendance"])

@router.post("/punch", response_model=AttendanceLogResponse, status_code=status.HTTP_201_CREATED)
def record_punch(
    payload: AttendancePunchRequest,
    db: Session = Depends(get_db),
    # For now, we allow the device to authenticate or we use a secure token.
    # In a real scenario, this might be a machine-to-machine token.
    # For this demo, we'll assume the clinic_id is part of the context or the user
    current_user = Depends(get_current_user)
):
    return AttendanceService(db).log_punch(current_user.clinic_id, payload)

@router.get("/logs", response_model=List[AttendanceLogResponse])
def get_attendance_logs(
    db: Session = Depends(get_db),
    current_user = Depends(require_clinic_admin)
):
    return AttendanceService(db).get_logs(current_user.clinic_id)
