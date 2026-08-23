"""Authentication endpoints."""

import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apps.api.auth.dependencies import require_demo_mode
from apps.api.auth.jwt import create_agent_token
from apps.api.auth.roles import get_agent_roles
from apps.api.config import settings
from apps.api.state import state

router = APIRouter()


class TokenRequest(BaseModel):
    agent_id: str
    bootstrap_token: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    agent_id: str
    expires_in_minutes: int
    label: str = "DEMO AUTHENTICATION — not for production"


@router.post("/token")
async def issue_token(request: TokenRequest):
    """Exchange demo credentials or the configured production bootstrap secret for a JWT."""
    if not settings.demo_mode:
        configured_token = settings.auth_bootstrap_token
        if not configured_token:
            raise HTTPException(
                status_code=503,
                detail="Production authentication bootstrap is not configured",
            )
        if not request.bootstrap_token or not secrets.compare_digest(
            request.bootstrap_token,
            configured_token,
        ):
            raise HTTPException(status_code=401, detail="Invalid bootstrap credentials")

    agent = state.get_agent(request.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    token = create_agent_token(agent.id)
    label = (
        "Production bootstrap authentication"
        if not settings.demo_mode
        else "DEMO AUTHENTICATION — not for production"
    )
    return TokenResponse(
        access_token=token,
        agent_id=agent.id,
        expires_in_minutes=settings.jwt_expire_minutes,
        label=label,
    )


@router.get("/demo-agents")
async def list_demo_tokens(_: None = Depends(require_demo_mode)):
    """List demo agents with pre-issued tokens for local development."""
    agents = state.list_agents()
    return {
        "label": "DEMO AUTHENTICATION — not for production",
        "agents": [
            {
                "agent_id": a.id,
                "agent_name": a.name,
                "access_token": create_agent_token(a.id),
                "roles": sorted(r.value for r in get_agent_roles(a)),
            }
            for a in agents
        ],
    }
