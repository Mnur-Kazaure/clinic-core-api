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
    Create database tables on startup (SQLite dev only).
    """
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(bind=engine)


# Register API v1
app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
