from typing import Generator
from sqlalchemy.orm import Session

def get_db() -> Generator[Session, None, None]:
    from app.core.database import SessionLocal  # 🔑 lazy import

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
