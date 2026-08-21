"""Agent endpoints."""

from fastapi import APIRouter, HTTPException, Query

from apps.api.state import state

router = APIRouter()


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
    agent_actions = state.list_actions(agent_id=agent_id, limit=10)
    return {
        "agent": agent,
        "recent_actions": agent_actions,
        "demo_mode": state.demo_mode,
    }
