"""FastAPI application entry point.

Purpose: Creates the API app, configures CORS, mounts route modules, and exposes
the /health endpoint for connectivity checks.
Interactions: Started by uvicorn (see README). Imports settings from config.py,
the documents router from api/documents.py, and database checks from database.py.
Called by the frontend via lib/api.ts and exercised by tests/test_documents.py.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.documents import router as documents_router
from app.api.rag import router as rag_router
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

app.include_router(documents_router)
app.include_router(rag_router)


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
