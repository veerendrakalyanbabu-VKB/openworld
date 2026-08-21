"""Health check endpoints."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from apps.api.state import state
from core.db.session import get_engine

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "openworld-api",
        "version": "0.2.0",
        "demo_mode": state.demo_mode,
    }


@router.get("/ready")
async def readiness_check():
    """Readiness probe — verifies database connectivity."""
    db_status = "unknown"
    try:
        if state._db_initialized:
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "connected"
        else:
            db_status = "not_initialized"
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": "openworld-api",
                "database": "unavailable",
                "demo_mode": state.demo_mode,
            },
        )
    if db_status != "connected":
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": "openworld-api",
                "database": db_status,
                "demo_mode": state.demo_mode,
            },
        )
    return {
        "status": "ready",
        "service": "openworld-api",
        "database": db_status,
        "demo_mode": state.demo_mode,
    }


@router.get("/stats")
async def get_stats():
    return state.get_stats()
