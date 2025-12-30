from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.models.base import Base  # ✅ single Base

# -------------------------------------------------------------------
# SQLAlchemy Engine
# -------------------------------------------------------------------

engine = create_engine(
    settings.DATABASE_URL,
    future=True,
    echo=False,
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
# Dependency Helper
# -------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()






# # app/core/database.py
# from typing import Generator

# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, declarative_base, Session

# from app.core.config import settings  # 🔒 single source of truth

# # -------------------------------------------------------------------
# # SQLAlchemy Engine
# # -------------------------------------------------------------------

# engine = create_engine(
#     settings.DATABASE_URL,
#     future=True,
#     echo=False,
# )

# # -------------------------------------------------------------------
# # Session Factory
# # -------------------------------------------------------------------

# SessionLocal = sessionmaker(
#     bind=engine,
#     class_=Session,
#     autoflush=False,
#     autocommit=False,
#     expire_on_commit=False,
# )

# # -------------------------------------------------------------------
# # Declarative Base
# # -------------------------------------------------------------------

# Base = declarative_base()

# # -------------------------------------------------------------------
# # Dependency Helper
# # -------------------------------------------------------------------

# def get_db() -> Generator[Session, None, None]:
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
