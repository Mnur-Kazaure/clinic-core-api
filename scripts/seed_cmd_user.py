# scripts/seed_cmd_user.py

import sys
import os
sys.path.append(os.getcwd())

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.core.auth.passwords import hash_password
from app.shared.enums import UserRole
import uuid

def seed_cmd():
    db = SessionLocal()
    try:
        # Get first clinic
        from app.models.clinic import Clinic
        clinic = db.query(Clinic).first()
        if not clinic:
            print("❌ No clinic found. Run seed_demo_data.py first.")
            return

        # Check if CMD exists
        existing = db.query(User).filter(User.email == "cmd@demo.com").first()
        if existing:
            print("✅ CMD user already exists: cmd@demo.com")
            return

        cmd_user = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email="cmd@demo.com",
            password_hash=hash_password("password123"),
            full_name="Chief Medical Director",
            role=UserRole.CMD,
            is_active=True
        )
        db.add(cmd_user)
        db.commit()
        print("✅ CMD user seeded: cmd@demo.com / password123")
    finally:
        db.close()

if __name__ == "__main__":
    seed_cmd()
