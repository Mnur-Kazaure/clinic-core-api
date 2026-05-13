# app/services/cmd_oversight_service.py - CMD Executive Oversight Logic

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.billing_ledger_entry import BillingLedgerEntry
from app.models.visit import Visit, VisitServiceLine, VisitStatus
from app.models.attendance_log import AttendanceLog
from app.models.event_log import EventLog
from app.models.user import User
from app.models.patient import Patient
from app.models.admission import Admission
from app.models.bed import Bed
from app.models.ward import Ward
from app.models.clinical_priority_event import ClinicalPriorityEvent
from app.models.admission_request import AdmissionRequest
from app.models.bed_assignment import BedAssignment
from app.models.follow_up import FollowUp
from app.shared.enums import (
    BillingEntryType, 
    AdmissionStatus, 
    BedStatus, 
    ClinicalPriorityLevel,
    AdmissionRequestStatus,
    UserRole,
    FollowUpStatus,
    FollowUpType
)
from datetime import datetime, timezone, timedelta

class CMDOversightService:
    def __init__(self, db: Session):
        self.db = db

    def get_executive_stats(self, clinic_id):
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # Financial Metrics
        revenue = self.db.query(func.sum(BillingLedgerEntry.amount_minor)).filter(
            BillingLedgerEntry.clinic_id == clinic_id,
            BillingLedgerEntry.entry_type == BillingEntryType.CHARGE,
            BillingLedgerEntry.occurred_at >= today_start
        ).scalar() or 0
        
        total_balance = self.db.query(func.sum(BillingLedgerEntry.amount_minor)).filter(
            BillingLedgerEntry.clinic_id == clinic_id
        ).scalar() or 0
        outstanding = max(0, total_balance)

        # Operational Metrics
        visits_count = self.db.query(Visit).filter(
            Visit.clinic_id == clinic_id,
            Visit.started_at >= today_start
        ).count()
        
        admissions = self.db.query(Admission).filter(
            Admission.clinic_id == clinic_id,
            Admission.admitted_at >= today_start
        ).count()
        
        discharges = self.db.query(Admission).filter(
            Admission.clinic_id == clinic_id,
            Admission.discharged_at >= today_start
        ).count()

        # Bed Occupancy (Calculated via Active Assignments)
        total_beds = self.db.query(Bed).filter(
            Bed.clinic_id == clinic_id,
            Bed.active == True
        ).count()
        occupied_beds = self.db.query(BedAssignment).filter(
            BedAssignment.clinic_id == clinic_id,
            BedAssignment.released_at == None
        ).count()
        bed_occupancy = (occupied_beds / total_beds * 100) if total_beds > 0 else 0

        # Staff Metrics
        clocked_in = self.db.query(func.count(func.distinct(AttendanceLog.user_id))).filter(
            AttendanceLog.clinic_id == clinic_id,
            AttendanceLog.punched_at >= today_start,
            AttendanceLog.punch_type == "PUNCH_IN"
        ).scalar() or 0

        # Clinical Service Line Counts
        opd_count = self.db.query(Visit).filter(
            Visit.clinic_id == clinic_id,
            Visit.service_line == VisitServiceLine.OPD,
            Visit.status != VisitStatus.COMPLETED,
            Visit.status != VisitStatus.CANCELLED
        ).count()
        
        anc_count = self.db.query(Visit).filter(
            Visit.clinic_id == clinic_id,
            Visit.service_line == VisitServiceLine.ANC,
            Visit.status != VisitStatus.COMPLETED,
            Visit.status != VisitStatus.CANCELLED
        ).count()
        
        maternity_count = self.db.query(Visit).filter(
            Visit.clinic_id == clinic_id,
            Visit.service_line == VisitServiceLine.MATERNITY,
            Visit.status != VisitStatus.COMPLETED,
            Visit.status != VisitStatus.CANCELLED
        ).count()

        # Alerts & Approvals
        emergencies = self.db.query(ClinicalPriorityEvent).filter(
            ClinicalPriorityEvent.clinic_id == clinic_id,
            ClinicalPriorityEvent.level == ClinicalPriorityLevel.CRITICAL,
            ClinicalPriorityEvent.set_at >= today_start
        ).count()

        pending_approvals = self.db.query(AdmissionRequest).filter(
            AdmissionRequest.clinic_id == clinic_id,
            AdmissionRequest.status == AdmissionRequestStatus.PENDING
        ).count()

        # Follow-Up & Continuity Metrics
        follow_ups_today = self.db.query(FollowUp).filter(
            FollowUp.clinic_id == clinic_id,
            FollowUp.due_at >= today_start,
            FollowUp.due_at < today_end
        ).count()

        missed_follow_ups = self.db.query(FollowUp).filter(
            FollowUp.clinic_id == clinic_id,
            FollowUp.due_at < now,
            FollowUp.status == FollowUpStatus.SCHEDULED
        ).count()

        chronic_monitoring = self.db.query(FollowUp).filter(
            FollowUp.clinic_id == clinic_id,
            FollowUp.type == FollowUpType.CHRONIC_RECALL,
            FollowUp.status == FollowUpStatus.SCHEDULED
        ).count()

        # Latest Attendance
        latest_logs = self.db.query(AttendanceLog, User.full_name, User.role).join(
            User, AttendanceLog.user_id == User.id
        ).filter(
            AttendanceLog.clinic_id == clinic_id
        ).order_by(AttendanceLog.punched_at.desc()).limit(10).all()

        attendance_data = []
        for log, name, role in latest_logs:
            attendance_data.append({
                "name": name,
                "role": role,
                "punch_type": log.punch_type,
                "punched_at": log.punched_at.isoformat(),
                "location": log.location
            })
        
        # New Operational Metrics
        thirty_mins_ago = now - timedelta(minutes=30)
        one_hour_ago = now - timedelta(hours=1)
        
        long_waiting = self.db.query(Visit).filter(
            Visit.clinic_id == clinic_id,
            Visit.status.in_([VisitStatus.REGISTERED]),
            Visit.started_at <= thirty_mins_ago
        ).count()
        
        delayed_consultations = self.db.query(Visit).filter(
            Visit.clinic_id == clinic_id,
            Visit.status == VisitStatus.IN_CONSULTATION,
            Visit.started_at <= one_hour_ago
        ).count()
        
        active_doctors = self.db.query(User).filter(
            User.clinic_id == clinic_id,
            User.role == UserRole.DOCTOR,
            User.is_active == True
        ).count()
        
        doctor_workload = 0
        if active_doctors > 0:
            active_consultations = self.db.query(Visit).filter(
                Visit.clinic_id == clinic_id,
                Visit.status == VisitStatus.IN_CONSULTATION
            ).count()
            doctor_workload = min(100, int((active_consultations / active_doctors) * 100))

        total_patients = self.db.query(Patient).filter(
            Patient.clinic_id == clinic_id
        ).count()

        return {
            "daily_revenue_minor": revenue,
            "patient_throughput": visits_count,
            "total_patients_count": total_patients,
            "staff_compliance_count": clocked_in,
            "system_health": "OPTIMAL",
            "opd_active_count": opd_count,
            "anc_active_count": anc_count,
            "maternity_active_count": maternity_count,
            "latest_attendance": attendance_data,
            "admissions_today": admissions,
            "discharges_today": discharges,
            "outstanding_payments_minor": outstanding,
            "bed_occupancy_percent": int(bed_occupancy),
            "emergency_alerts_count": emergencies,
            "pending_approvals_count": pending_approvals,
            "suspicious_activities_count": 0,
            "long_waiting_count": long_waiting,
            "delayed_consultations_count": delayed_consultations,
            "doctor_workload_percent": doctor_workload,
            "follow_ups_today": follow_ups_today,
            "missed_follow_ups": missed_follow_ups,
            "chronic_monitoring_count": chronic_monitoring
        }

    def get_live_activity(self, clinic_id, limit=50):
        return self.db.query(EventLog).filter(
            EventLog.clinic_id == clinic_id
        ).order_by(EventLog.created_at.desc()).limit(limit).all()

    def get_ward_occupancy(self, clinic_id):
        wards = self.db.query(Ward).filter(Ward.clinic_id == clinic_id, Ward.active == True).all()
        results = []
        for w in wards:
            capacity = self.db.query(Bed).filter(Bed.ward_id == w.id, Bed.active == True).count()
            occupied = self.db.query(BedAssignment).filter(
                BedAssignment.clinic_id == clinic_id,
                BedAssignment.released_at == None
            ).join(Bed).filter(Bed.ward_id == w.id).count()
            
            # Count critical patients in this ward
            critical = self.db.query(ClinicalPriorityEvent).join(
                Visit, ClinicalPriorityEvent.visit_id == Visit.id
            ).filter(
                Visit.clinic_id == clinic_id,
                ClinicalPriorityEvent.level == ClinicalPriorityLevel.CRITICAL
            ).join(Admission, Visit.patient_id == Admission.patient_id).filter(
                Admission.status == AdmissionStatus.ACTIVE
            ).join(BedAssignment, Admission.id == BedAssignment.admission_id).filter(
                BedAssignment.released_at == None
            ).join(Bed).filter(Bed.ward_id == w.id).count()

            results.append({
                "name": w.name,
                "capacity": capacity,
                "occupied": occupied,
                "critical": critical,
                "ward_type": w.ward_type
            })
        return results

    def get_staff_performance(self, clinic_id):
        staff = self.db.query(User).filter(User.clinic_id == clinic_id).all()
        results = []
        for s in staff:
            punches = self.db.query(AttendanceLog).filter(AttendanceLog.user_id == s.id).count()
            actions = self.db.query(EventLog).filter(EventLog.actor_id == s.id).count()
            results.append({
                "user_id": s.id,
                "full_name": s.full_name or "Unknown",
                "role": s.role,
                "punch_count": punches,
                "clinical_action_count": actions
            })
        return results
