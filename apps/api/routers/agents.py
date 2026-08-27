"""Agent endpoints."""

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from apps.api.auth.dependencies import AuthenticatedActor, require_system_admin
from apps.api.state import state
from core.models.agent import Agent, AgentStatus
from core.models.capability import KNOWN_CAPABILITY_IDS, canonicalize_action, is_unrestricted_wildcard
from core.utils.time import utc_now

router = APIRouter()


class AgentCreateRequest(BaseModel):
    id: str | None = None
    name: str
    owner: str
    organization: str = "default"
    description: str = ""
    status: AgentStatus = AgentStatus.ACTIVE
    capabilities: list[str] = Field(default_factory=list)


class AgentUpdateRequest(BaseModel):
    name: str | None = None
    owner: str | None = None
    organization: str | None = None
    description: str | None = None
    status: AgentStatus | None = None
    capabilities: list[str] | None = None


def _slug_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"agent-{slug or uuid.uuid4().hex[:8]}"


def _validate_capabilities(capabilities: list[str]) -> list[str]:
    canonical: list[str] = []
    for raw in capabilities:
        cap = canonicalize_action(raw)
        if is_unrestricted_wildcard(cap):
            raise HTTPException(status_code=400, detail="Unrestricted wildcard capabilities are not allowed")
        if cap not in KNOWN_CAPABILITY_IDS and not cap.startswith("test."):
            raise HTTPException(status_code=400, detail=f"Unknown capability: {cap}")
        if cap not in canonical:
            canonical.append(cap)
    return canonical


@router.get("")
async def list_agents(
    search: str | None = Query(None),
    status: str | None = Query(None),
):
    agents = state.list_agents()
    if search:
        agents = [
            a for a in agents
            if search.lower() in a.name.lower() or search.lower() in a.description.lower()
        ]
    if status:
        agents = [a for a in agents if a.status.value == status]
    return {"agents": agents, "total": len(agents), "demo_mode": state.demo_mode}


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    agent = state.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent_actions = state.list_actions(agent_id=agent_id, limit=20)
    policies = [
        p for p in state.list_policies()
        if any((r.agent_match or "") in ("*", agent.name, agent.id) for r in p.rules)
    ]
    verified = sum(1 for a in agent_actions if a.status.value == "verified")
    failed = sum(1 for a in agent_actions if a.status.value in ("failed", "verification_failed", "blocked", "denied"))
    verification_rate = round((verified / max(len(agent_actions), 1)) * 100, 1)
    return {
        "agent": agent,
        "recent_actions": agent_actions,
        "policies": policies,
        "metrics": {
            "recent_action_count": len(agent_actions),
            "verified": verified,
            "failed_or_blocked": failed,
            "verification_rate": verification_rate,
            "source": "application_state",
        },
        "demo_mode": state.demo_mode,
    }


@router.post("")
async def create_agent(
    request: AgentCreateRequest,
    actor: AuthenticatedActor = Depends(require_system_admin),
):
    agent_id = request.id or _slug_id(request.name)
    if state.get_agent(agent_id):
        raise HTTPException(status_code=409, detail="Agent already exists")
    capabilities = _validate_capabilities(request.capabilities)
    agent = Agent(
        id=agent_id,
        name=request.name,
        description=request.description,
        owner=request.owner,
        organization=request.organization,
        status=request.status,
        capabilities=capabilities,
        metadata={"created_by": actor.agent.id},
    )
    state.save_agent(agent)
    return {"agent": agent, "created_by": actor.agent.id, "demo_mode": state.demo_mode}


@router.patch("/{agent_id}")
async def update_agent(
    agent_id: str,
    request: AgentUpdateRequest,
    actor: AuthenticatedActor = Depends(require_system_admin),
):
    agent = state.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if request.name is not None:
        agent.name = request.name
    if request.owner is not None:
        agent.owner = request.owner
    if request.organization is not None:
        agent.organization = request.organization
    if request.description is not None:
        agent.description = request.description
    if request.status is not None:
        agent.status = request.status
    if request.capabilities is not None:
        agent.capabilities = _validate_capabilities(request.capabilities)
    agent.updated_at = utc_now()
    state.save_agent(agent)
    return {"agent": agent, "updated_by": actor.agent.id, "demo_mode": state.demo_mode}
