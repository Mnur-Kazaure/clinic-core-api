# app/services/attendance_service.py

from sqlalchemy.orm import Session
from app.models.attendance_log import AttendanceLog
from app.schemas.attendance import AttendancePunchRequest
from app.models.user import User
from fastapi import HTTPException, status
from uuid import UUID

class AttendanceService:
    def __init__(self, db: Session):
        self.db = db

    def log_punch(self, clinic_id: UUID, payload: AttendancePunchRequest) -> AttendanceLog:
        # Verify user exists and belongs to clinic
        user = self.db.query(User).filter(User.id == payload.user_id, User.clinic_id == clinic_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in this clinic"
            )

        log = AttendanceLog(
            clinic_id=clinic_id,
            user_id=payload.user_id,
            punch_type=payload.punch_type,
            hardware_ref=payload.hardware_ref,
            location=payload.location,
            device_metadata=payload.device_metadata
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_logs(self, clinic_id: UUID, user_id: UUID | None = None):
        query = self.db.query(AttendanceLog).filter(AttendanceLog.clinic_id == clinic_id)
        if user_id:
            query = query.filter(AttendanceLog.user_id == user_id)
        return query.order_by(AttendanceLog.punched_at.desc()).all()
