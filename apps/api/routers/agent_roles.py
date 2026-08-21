"""Agent role administration endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from apps.api.auth.dependencies import AuthenticatedActor, get_authenticated_actor, require_system_admin
from apps.api.auth.roles import Role, get_agent_roles, has_any_role
from apps.api.state import state
from core.governance.roles import assign_role, revoke_role, roles_from_metadata

router = APIRouter()


class RoleAssignRequest(BaseModel):
    role: str = Field(..., description="Role to assign (operator, policy_admin, system_admin)")


def _parse_role(value: str) -> Role:
    try:
        return Role(value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role") from exc


def _can_view_roles(actor: AuthenticatedActor, target_agent_id: str) -> bool:
    if actor.agent.id == target_agent_id:
        return True
    return has_any_role(actor.roles, Role.SYSTEM_ADMIN)


@router.get("/{agent_id}/roles")
async def list_agent_roles(
    agent_id: str,
    actor: AuthenticatedActor = Depends(get_authenticated_actor),
):
    if not _can_view_roles(actor, agent_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient authorization")
    agent = state.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    resolved = sorted(r.value for r in get_agent_roles(agent))
    stored = roles_from_metadata(agent)
    return {
        "agent_id": agent_id,
        "roles": resolved,
        "stored_roles": stored,
        "demo_mode": state.demo_mode,
    }


@router.post("/{agent_id}/roles")
async def assign_agent_role(
    agent_id: str,
    body: RoleAssignRequest,
    request: Request,
    actor: AuthenticatedActor = Depends(require_system_admin),
):
    target = state.get_agent(agent_id)
    if not target:
        raise HTTPException(status_code=404, detail="Agent not found")
    role = _parse_role(body.role)
    correlation_id = request.headers.get("X-Request-ID", "")
    updated, old_roles, new_roles = assign_role(
        target=target,
        role=role,
        actor_id=actor.agent.id,
        all_agents=state.list_agents(),
        audit_logger=state.audit_logger,
        correlation_id=correlation_id,
    )
    state.save_agent(updated)
    state.reload_agent(agent_id)
    return {
        "agent_id": agent_id,
        "old_roles": old_roles,
        "new_roles": new_roles,
        "assigned_by": actor.agent.id,
        "demo_mode": state.demo_mode,
    }


@router.delete("/{agent_id}/roles/{role_name}")
async def revoke_agent_role(
    agent_id: str,
    role_name: str,
    request: Request,
    actor: AuthenticatedActor = Depends(require_system_admin),
):
    target = state.get_agent(agent_id)
    if not target:
        raise HTTPException(status_code=404, detail="Agent not found")
    role = _parse_role(role_name)
    correlation_id = request.headers.get("X-Request-ID", "")
    updated, old_roles, new_roles = revoke_role(
        target=target,
        role=role,
        actor_id=actor.agent.id,
        all_agents=state.list_agents(),
        audit_logger=state.audit_logger,
        correlation_id=correlation_id,
    )
    state.save_agent(updated)
    state.reload_agent(agent_id)
    return {
        "agent_id": agent_id,
        "old_roles": old_roles,
        "new_roles": new_roles,
        "revoked_by": actor.agent.id,
        "demo_mode": state.demo_mode,
    }
