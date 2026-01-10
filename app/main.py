# app/main.py
from fastapi import FastAPI
from app.api.v1.router import api_router
from app.core.database import engine
from app.models import Base

app = FastAPI(
    title="Clinic MVP",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup() -> None:
    """
    Create database tables on startup (DEV ONLY).
    """
    Base.metadata.create_all(bind=engine)


# Register API v1
app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}