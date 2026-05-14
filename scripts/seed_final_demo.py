from __future__ import annotations
import uuid
from datetime import date, datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import SessionLocal
from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.visit import Visit, VisitServiceLine, VisitStatus
from app.models.admission import Admission
from app.models.bed import Bed
from app.models.ward import Ward
from app.models.billing_ledger_entry import BillingLedgerEntry
from app.models.attendance_log import AttendanceLog
from app.models.event_log import EventLog
from app.models.clinical_priority_event import ClinicalPriorityEvent
from app.models.bed_assignment import BedAssignment
from app.core.auth.passwords import hash_password
from app.shared.enums import (
    UserRole, 
    BillingEntryType, 
    BillingReasonCode, 
    AdmissionType, 
    AdmissionStatus, 
    BedStatus,
    ClinicalPriorityLevel,
    ClinicalPrioritySource,
    BedAssignmentType,
    WardType
)

def seed_final():
    db = SessionLocal()
    try:
        # 1. Ensure Consistent Clinic
        clinic_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
        if not clinic:
            clinic = Clinic(id=clinic_id, name="Hospital Command Center Demo", billing_currency="NGN")
            db.add(clinic)
            db.flush()
        else:
            clinic.name = "Hospital Command Center Demo"
        
        # 2. Seed All System Roles with password123
        roles = [
            (UserRole.CMD, "cmd@demo.com", "Chief Medical Director"),
            (UserRole.RECEPTION, "reception@demo.com", "Reception Lead"),
            (UserRole.DOCTOR, "doctor@demo.com", "Dr. Sarah Bello"),
            (UserRole.MIDWIFE, "nurse@demo.com", "Nurse Amaka"),
            (UserRole.ADMIN, "admin@demo.com", "System Admin"),
            (UserRole.LAB, "lab@demo.com", "Lab Scientist"),
            (UserRole.PHARMACY, "pharmacy@demo.com", "Pharmacist"),
        ]

        hashed_pwd = hash_password("password123")
        
        for role, email, name in roles:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    email=email,
                    password_hash=hashed_pwd,
                    full_name=name,
                    role=role,
                    is_active=True
                )
                db.add(user)
            else:
                user.clinic_id = clinic.id
                user.password_hash = hashed_pwd
                user.role = role
        
        db.flush()

        # 3. Create Patients
        patient_names = [
            "Aisha Garba", "Umar Faruq", "Chidi Okafor", "Fatima Sani", 
            "Bello Idris", "Ngozi Adeleke", "Mustapha Yusuf", "Khadija Lawal",
            "Olumide Bakare", "Maryam Tukur", "Zainab Abubakar", "Ibrahim Danlami",
            "Sani Abacha", "Aminu Kano", "Hadiza Bala", "Grace Okon",
            "Emeka Nwosu", "Babatunde Raji", "Funke Akindele", "Chukwuma Soludo"
        ]
        
        seeded_patients = []
        for i, name in enumerate(patient_names):
            p = db.query(Patient).filter(Patient.full_name == name, Patient.clinic_id == clinic.id).first()
            if not p:
                p = Patient(
                    id=uuid.uuid4(), clinic_id=clinic.id, full_name=name, 
                    date_of_birth=date(1975 + (i//2), (i%12)+1, (i*3)%28 + 1), 
                    gender="MALE" if i % 2 == 0 else "FEMALE", 
                    phone_number=f"0803{i}000000"[:11], 
                    address=f"Kano Housing Estate, Block {i}",
                    occupation="Business"
                )
                db.add(p)
            seeded_patients.append(p)
        db.flush()

        # 4. Create Wards & Beds
        ward = db.query(Ward).filter(Ward.name == "Main Medical Ward", Ward.clinic_id == clinic.id).first()
        if not ward:
            ward = Ward(id=uuid.uuid4(), clinic_id=clinic.id, name="Main Medical Ward", ward_type=WardType.GENERAL)
            db.add(ward)
            db.flush()
        
        for i in range(1, 16):
            bed_label = f"BED-{i:02d}"
            bed = db.query(Bed).filter(Bed.ward_id == ward.id, Bed.bed_label == bed_label).first()
            if not bed:
                db.add(Bed(id=uuid.uuid4(), clinic_id=clinic.id, ward_id=ward.id, bed_label=bed_label, status=BedStatus.AVAILABLE))
        
        db.flush()

        # 5. Create Active Clinical Activity (Today)
        now = datetime.now(timezone.utc)
        doctor = db.query(User).filter(User.role == UserRole.DOCTOR, User.clinic_id == clinic.id).first()
        cashier = db.query(User).filter(User.role == UserRole.ADMIN, User.clinic_id == clinic.id).first()

        for i, p in enumerate(seeded_patients[:15]):
            # Create a visit
            v = Visit(
                id=uuid.uuid4(), clinic_id=clinic.id, patient_id=p.id, 
                assigned_doctor_id=doctor.id,
                service_line=VisitServiceLine.OPD if i % 3 != 0 else (VisitServiceLine.ANC if i % 3 == 1 else VisitServiceLine.MATERNITY), 
                status=VisitStatus.REGISTERED if i < 5 else (VisitStatus.IN_CONSULTATION if i < 10 else VisitStatus.PHARMACY_PENDING), 
                started_at=now - timedelta(minutes=15 * i)
            )
            db.add(v)
            
            # Revenue
            db.add(BillingLedgerEntry(
                id=uuid.uuid4(), clinic_id=clinic.id, patient_id=p.id, visit_id=v.id, 
                entry_type=BillingEntryType.CHARGE, amount_minor=250000, currency="NGN", 
                description="Consultation Fee", reason_code=BillingReasonCode.SERVICE,
                actor_id=cashier.id, actor_role="ADMIN", occurred_at=now - timedelta(minutes=10 * i)
            ))
            
            # Event Log (LINKED)
            db.add(EventLog(
                id=uuid.uuid4(), event_type="REGISTRATION" if i < 10 else "ADMISSION_REQUEST", 
                clinic_id=clinic.id, 
                actor_id=cashier.id, actor_role="ADMIN", 
                patient_id=p.id,
                payload=f"Patient {p.full_name} processed for {v.service_line.value}"
            ))

        db.commit()
        print("✅ SUCCESS: Unified demo system seeded.")
        print(f"Clinic: {clinic.name} ({clinic.id})")
        print(f"Users: cmd@demo.com, reception@demo.com, etc. (Password: password123)")
    except Exception as e:
        db.rollback()
        print(f"❌ ERROR seeding data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_final()
