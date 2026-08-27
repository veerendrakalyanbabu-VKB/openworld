"""Capability catalog endpoints."""

from fastapi import APIRouter

from apps.api.state import state
from core.models.capability import catalog_capabilities

router = APIRouter()


@router.get("")
async def list_capabilities():
    capabilities = catalog_capabilities()
    return {
        "capabilities": capabilities,
        "total": len(capabilities),
        "demo_mode": state.demo_mode,
        "note": "Agents may only be granted explicit catalog capabilities. Wildcards are rejected.",
    }
