# app/api/v1/cmd_oversight.py - CMD Executive API Routes

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.shared.enums import UserRole
from app.schemas.cmd_oversight import ExecutiveStatsResponse, ActivityFeedItem, StaffPerformanceItem
from app.services.cmd_oversight_service import CMDOversightService
from typing import List
from fastapi import HTTPException, status

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
