# # app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.database import engine
from app.core.middleware import reject_break_glass_on_write
from app.models import Base

app = FastAPI(
    title="Clinic MVP",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Set-Cookie"],
)

app.middleware("http")(reject_break_glass_on_write)

@app.on_event("startup")
def on_startup() -> None:
    """
    Ensure database tables exist and synchronize data for universal sharing.
    """
    from app.core.database import SessionLocal
    from app.models.clinic import Clinic
    from app.models.user import User
    from app.models.patient import Patient
    from app.shared.enums import UserRole
    from app.core.auth.passwords import hash_password
    import uuid

    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(bind=engine)

    # Universal Sync Logic for Demo Hardening
    db = SessionLocal()
    try:
        # 1. Ensure Universal Demo Clinic
        demo_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        clinic = db.query(Clinic).filter(Clinic.id == demo_id).first()
        if not clinic:
            clinic = Clinic(id=demo_id, name="Universal Command Center", billing_currency="NGN")
            db.add(clinic)
            db.flush()
        
        # 2. Standardize Demo Accounts
        hp = hash_password("password123")
        standard_users = [
            ("cmd@demo.com", UserRole.CMD, "Chief Medical Director"),
            ("reception@demo.com", UserRole.RECEPTION, "Reception Lead"),
            ("doctor@demo.com", UserRole.DOCTOR, "Dr. Sarah Bello"),
            ("nurse@demo.com", UserRole.MIDWIFE, "Nurse Amaka"),
            ("admin@demo.com", UserRole.ADMIN, "System Admin"),
            ("lab@demo.com", UserRole.LAB, "Lab Scientist"),
            ("pharmacy@demo.com", UserRole.PHARMACY, "Pharmacist"),
        ]

        for email, role, name in standard_users:
            u = db.query(User).filter(User.email == email).first()
            if not u:
                u = User(id=uuid.uuid4(), email=email, full_name=name)
                db.add(u)
            u.clinic_id = demo_id
            u.password_hash = hp
            u.role = role
            u.is_active = True
        
        # 3. Universalize ALL Existing Users & Patients
        all_users = db.query(User).all()
        for u in all_users:
            u.clinic_id = demo_id
            if not u.password_hash or u.password_hash == "demo":
                u.password_hash = hp
        
        patients = db.query(Patient).all()
        for p in patients:
            p.clinic_id = demo_id
            
        db.commit()
    except Exception as e:
        print(f"Sync error: {e}")
        db.rollback()
    finally:
        db.close()


# Register API v1
app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
