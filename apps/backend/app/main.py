from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import check_database_connection

app = FastAPI(
    title="Aviation Intelligence Platform API",
    version="0.1.0",
    description="Backend API for the Aviation Intelligence AI Platform MVP.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict:
    db_ok, db_error = check_database_connection()
    status = "healthy" if db_ok else "degraded"

    return {
        "status": status,
        "service": "aviation-intelligence-backend",
        "database": {
            "connected": db_ok,
            "error": db_error,
        },
    }
