# app/main.py
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




# from fastapi import FastAPI

# from app.api.v1.router import api_router
# from app.core.config import settings

# app = FastAPI(
#     title="Clinic MVP",
#     version="0.1.0",
# )

# # Register API v1
# app.include_router(api_router)


# @app.get("/health")
# def health_check():
#     return {"status": "ok"}


# # 🔍 Diagnostic endpoint (temporary, for cURL testing)
# @app.get("/debug")
# def debug():
#     return {
#         "app": "running",
#         "api_v1": "loaded",
#         "visits": "reachable",
#         "labs": "reachable",
#         "pharmacy": "reachable",
#     }