import uuid
from datetime import date, datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
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

DATABASE_URL = "sqlite:///clinic.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



def seed_demo():
    db = SessionLocal()
    try:
        # 1. Get or Create Clinic (Matching the user's active clinic: "Demo Clinic")
        clinic = db.query(Clinic).filter(Clinic.name == "Demo Clinic").first()
        if not clinic:
            # Fallback to first available clinic or create if totally empty
            clinic = db.query(Clinic).first()
            if not clinic:
                clinic = Clinic(id=uuid.uuid4(), name="Demo Clinic", billing_currency="NGN")
                db.add(clinic)
                db.commit()
                db.refresh(clinic)
        
        # 2. Get or Create CMD User
        cmd_user = db.query(User).filter(User.email == "cmd@ksh.gov.ng").first()
        if not cmd_user:
            cmd_user = User(
                id=uuid.uuid4(), 
                email="cmd@ksh.gov.ng", 
                full_name="Dr. Ibrahim Musa", 
                role=UserRole.CMD, 
                clinic_id=clinic.id,
                password_hash="demo" 
            )
            db.add(cmd_user)
        else:
            # Ensure the existing CMD user is tied to the correct clinic
            cmd_user.clinic_id = clinic.id
        
        # 3. Create other staff
        doctor = db.query(User).filter(User.email == "doctor@ksh.gov.ng").first()
        if not doctor:
            doctor = User(id=uuid.uuid4(), full_name="Dr. Sarah Bello", role=UserRole.DOCTOR, clinic_id=clinic.id, password_hash="demo", email="doctor@ksh.gov.ng")
            db.add(doctor)
            
        midwife = db.query(User).filter(User.email == "nurse@ksh.gov.ng").first()
        if not midwife:
            midwife = User(id=uuid.uuid4(), full_name="Nurse Amaka", role=UserRole.MIDWIFE, clinic_id=clinic.id, password_hash="demo", email="nurse@ksh.gov.ng")
            db.add(midwife)
            
        cashier = db.query(User).filter(User.email == "cashier@ksh.gov.ng").first()
        if not cashier:
            cashier = User(id=uuid.uuid4(), full_name="John Finance", role=UserRole.ADMIN, clinic_id=clinic.id, password_hash="demo", email="cashier@ksh.gov.ng")
            db.add(cashier)
        db.commit()

        # 4. Create Patients (Adding 10 more as requested)
        patient_names = [
            "Aisha Garba", "Umar Faruq", "Chidi Okafor", "Fatima Sani", 
            "Bello Idris", "Ngozi Adeleke", "Mustapha Yusuf", "Khadija Lawal",
            "Olumide Bakare", "Maryam Tukur"
        ]
        
        seeded_patients = []
        for i, name in enumerate(patient_names):
            p = db.query(Patient).filter(Patient.full_name == name).first()
            if not p:
                p = Patient(
                    id=uuid.uuid4(), clinic_id=clinic.id, full_name=name, 
                    date_of_birth=date(1970 + (i*3), (i%12)+1, (i*2)%28 + 1), 
                    gender="MALE" if i % 2 == 0 else "FEMALE", 
                    phone_number=f"0803{i}234567", address=f"Kano Block {i}",
                    occupation="Civil Servant"
                )
                db.add(p)
            seeded_patients.append(p)
        db.commit()

        # 5. Create Wards & Beds
        ward = db.query(Ward).filter(Ward.name == "Male Medical Ward", Ward.clinic_id == clinic.id).first()
        if not ward:
            ward = Ward(id=uuid.uuid4(), clinic_id=clinic.id, name="Male Medical Ward", ward_type=WardType.GENERAL)
            db.add(ward)
            db.commit()
        
        beds = db.query(Bed).filter(Bed.ward_id == ward.id).all()
        if not beds:
            beds = []
            for i in range(1, 21): # Increased to 20 beds
                beds.append(Bed(id=uuid.uuid4(), clinic_id=clinic.id, ward_id=ward.id, bed_label=f"B-{i}", status=BedStatus.AVAILABLE))
            db.add_all(beds)
            db.commit()

        # 6. Create Clinical Data (Today)
        now = datetime.now(timezone.utc)
        
        # Simulated Activity for new patients
        for i, p in enumerate(seeded_patients):
            # Create a visit for each
            v = Visit(
                id=uuid.uuid4(), clinic_id=clinic.id, patient_id=p.id, 
                assigned_doctor_id=doctor.id,
                service_line=VisitServiceLine.OPD if i % 2 == 0 else VisitServiceLine.ANC, 
                status=VisitStatus.REGISTERED if i < 5 else VisitStatus.IN_CONSULTATION, 
                started_at=now - timedelta(minutes=10 * i)
            )
            db.add(v)
            
            # Add some revenue
            db.add(BillingLedgerEntry(
                id=uuid.uuid4(), clinic_id=clinic.id, patient_id=p.id, visit_id=v.id, 
                entry_type=BillingEntryType.CHARGE, amount_minor=250000, currency="NGN", 
                description="Consultation Fee", reason_code=BillingReasonCode.SERVICE,
                actor_id=cashier.id, actor_role="CASHIER", occurred_at=now - timedelta(minutes=5 * i)
            ))
            
            # Add event log
            db.add(EventLog(
                id=uuid.uuid4(), event_type="REGISTRATION", clinic_id=clinic.id, 
                actor_id=cashier.id, actor_role="CASHIER", 
                patient_id=p.id,
                payload=f"Patient {p.full_name} registered for {v.service_line.value}"
            ))

        db.commit()
        print("Demo data seeded successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo()
