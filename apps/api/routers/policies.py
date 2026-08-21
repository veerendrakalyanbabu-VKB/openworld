"""Policy endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from apps.api.auth.dependencies import AuthenticatedActor, require_policy_admin
from apps.api.state import state
from core.governance.policies import apply_policy_enablement, apply_policy_update, snapshot_policy
from core.models.audit import AuditEventType
from core.models.policy import Policy, PolicyRule

router = APIRouter()


class PolicyCreateRequest(BaseModel):
    id: str
    name: str
    description: str = ""
    rules: list[PolicyRule] = Field(default_factory=list)


class PolicyUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    rules: list[PolicyRule] | None = None


@router.get("")
async def list_policies():
    policies = state.list_policies()
    return {"policies": policies, "total": len(policies), "demo_mode": state.demo_mode}


@router.get("/{policy_id}")
async def get_policy(policy_id: str):
    policy = state.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"policy": policy, "demo_mode": state.demo_mode}


@router.get("/{policy_id}/versions")
async def list_policy_versions(policy_id: str):
    if not state.get_policy(policy_id):
        raise HTTPException(status_code=404, detail="Policy not found")
    versions = state.list_policy_versions(policy_id)
    return {"policy_id": policy_id, "versions": versions, "total": len(versions), "demo_mode": state.demo_mode}


@router.get("/{policy_id}/versions/{version_id}")
async def get_policy_version(policy_id: str, version_id: str):
    version = state.get_policy_version(version_id)
    if not version or version["policy_id"] != policy_id:
        raise HTTPException(status_code=404, detail="Policy version not found")
    return {"version": version, "demo_mode": state.demo_mode}


@router.post("")
async def create_policy(
    request: PolicyCreateRequest,
    http_request: Request,
    actor: AuthenticatedActor = Depends(require_policy_admin),
):
    if state.get_policy(request.id):
        raise HTTPException(status_code=409, detail="Policy already exists")

    policy = Policy(
        id=request.id,
        name=request.name,
        description=request.description,
        rules=request.rules,
    )
    correlation_id = http_request.headers.get("X-Request-ID", "")
    snapshot = snapshot_policy(policy, change_action="created", created_by=actor.agent.id)
    snapshot["id"] = str(uuid.uuid4())
    state.save_policy_snapshot(snapshot)
    state.save_policy(policy)
    state.audit_logger.log(
        AuditEventType.POLICY_CREATED,
        actor=actor.agent.id,
        subject=policy.id,
        action="create",
        policy_id=policy.id,
        details={"version": policy.version, "snapshot_id": snapshot["id"]},
        correlation_id=correlation_id,
    )
    return {
        "policy": policy,
        "demo_mode": state.demo_mode,
        "created_by": actor.agent.id,
    }


@router.put("/{policy_id}")
async def update_policy(
    policy_id: str,
    request: PolicyUpdateRequest,
    http_request: Request,
    actor: AuthenticatedActor = Depends(require_policy_admin),
):
    policy = state.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    correlation_id = http_request.headers.get("X-Request-ID", "")
    updated, snapshot = apply_policy_update(
        policy,
        name=request.name,
        description=request.description,
        rules=request.rules,
        actor_id=actor.agent.id,
        audit_logger=state.audit_logger,
        correlation_id=correlation_id,
    )
    state.save_policy_snapshot(snapshot)
    state.save_policy(updated)
    return {
        "policy": updated,
        "version_snapshot_id": snapshot["id"],
        "updated_by": actor.agent.id,
        "demo_mode": state.demo_mode,
    }


@router.post("/{policy_id}/disable")
async def disable_policy(
    policy_id: str,
    http_request: Request,
    actor: AuthenticatedActor = Depends(require_policy_admin),
):
    policy = state.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    correlation_id = http_request.headers.get("X-Request-ID", "")
    was_enabled = policy.enabled
    updated, snapshot = apply_policy_enablement(
        policy,
        enabled=False,
        actor_id=actor.agent.id,
        audit_logger=state.audit_logger,
        correlation_id=correlation_id,
    )
    if was_enabled != updated.enabled:
        state.save_policy_snapshot(snapshot)
    state.save_policy(updated)
    return {"policy": updated, "disabled_by": actor.agent.id, "demo_mode": state.demo_mode}


@router.post("/{policy_id}/enable")
async def enable_policy(
    policy_id: str,
    http_request: Request,
    actor: AuthenticatedActor = Depends(require_policy_admin),
):
    policy = state.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    correlation_id = http_request.headers.get("X-Request-ID", "")
    was_enabled = policy.enabled
    updated, snapshot = apply_policy_enablement(
        policy,
        enabled=True,
        actor_id=actor.agent.id,
        audit_logger=state.audit_logger,
        correlation_id=correlation_id,
    )
    if was_enabled != updated.enabled:
        state.save_policy_snapshot(snapshot)
    state.save_policy(updated)
    return {"policy": updated, "enabled_by": actor.agent.id, "demo_mode": state.demo_mode}
