# app/core/database.py
import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# -------------------------------------------------------------------
# Database URL (single source of truth)
# -------------------------------------------------------------------

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./app.db",  # dev-safe fallback
)

# -------------------------------------------------------------------
# SQLAlchemy Engine
# -------------------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    future=True,
    echo=False,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
)

# -------------------------------------------------------------------
# Session Factory
# -------------------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

# -------------------------------------------------------------------
# Declarative Base
# -------------------------------------------------------------------

Base = declarative_base()

# -------------------------------------------------------------------
# Dependency Helper (optional but useful)
# -------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    Provides a SQLAlchemy DB session per request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
