"""Health check endpoints."""

from fastapi import APIRouter

from apps.api.state import state

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "openworld-api",
        "version": "0.1.0",
        "demo_mode": state.demo_mode,
    }


@router.get("/stats")
async def get_stats():
    return state.get_stats()
