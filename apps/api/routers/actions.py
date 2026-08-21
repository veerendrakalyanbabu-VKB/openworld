"""Action endpoints."""

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.auth.dependencies import get_current_agent
from apps.api.state import state
from core.db.session import get_db
from core.idempotency.service import IdempotencyConflictError, IdempotencyService, hash_request
from core.models.agent import Agent

router = APIRouter()


class ActionCreateRequest(BaseModel):
    action: str
    target: str = ""
    parameters: dict = Field(default_factory=dict)
    context: dict = Field(default_factory=dict)
    requested_permissions: list[str] = Field(default_factory=list)
    auto_approve: bool = False
    # Deprecated: identity comes from JWT; body agent_id is ignored
    agent_id: str | None = None


@router.get("")
async def list_actions(
    agent_id: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
):
    actions = state.list_actions(agent_id=agent_id, status=status, limit=limit)
    return {"actions": actions, "total": len(actions), "demo_mode": state.demo_mode}


@router.get("/{action_id}")
async def get_action(action_id: str):
    action = state.get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return {"action": action, "demo_mode": state.demo_mode}


@router.post("")
async def create_action(
    request: ActionCreateRequest,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    req_hash = hash_request(agent.id, request.action, request.parameters, request.target)

    if idempotency_key:
        svc = IdempotencyService(db)
        try:
            cached = svc.check(agent.id, idempotency_key, req_hash)
            if cached is not None:
                return cached
        except IdempotencyConflictError:
            raise HTTPException(
                status_code=409,
                detail="Idempotency key reused with different request",
            ) from None

    action = state.lifecycle.create_action(
        agent_id=agent.id,
        agent_name=agent.name,
        action=request.action,
        target=request.target,
        parameters=request.parameters,
        context=request.context,
        requested_permissions=request.requested_permissions or [request.action],
    )
    result = await state.lifecycle.process(action, agent=agent, auto_approve=request.auto_approve)

    approval_status = None
    if result.status.value == "pending_approval":
        approval_status = "pending"
    state.save_action(result, approval_status=approval_status)

    response = {"action": result.model_dump(mode="json"), "demo_mode": state.demo_mode}

    if idempotency_key:
        IdempotencyService(db).store(
            agent.id,
            idempotency_key,
            req_hash,
            result.id,
            response,
        )

    return response


class SimulateRequest(BaseModel):
    action: str
    target: str = ""
    parameters: dict = Field(default_factory=dict)
    agent_id: str | None = None


@router.post("/simulate")
async def simulate_action(
    request: SimulateRequest,
    agent: Agent = Depends(get_current_agent),
):
    from core.identity.validator import IdentityValidator
    from core.permissions.validator import PermissionValidator

    action = state.lifecycle.create_action(
        agent_id=agent.id,
        agent_name=agent.name,
        action=request.action,
        target=request.target,
        parameters=request.parameters,
    )
    identity_result = IdentityValidator().validate(agent)
    permission_result = PermissionValidator().validate(agent, request.action)
    policy_result = state.policy_engine.simulate(action, agent.name)
    risk_result = state.risk_engine.assess(
        action, historical_reliability=agent.trust_dimensions.reliability
    )

    predicted_outcome = "allow"
    if (
        not identity_result.valid
        or not permission_result.permitted
        or policy_result["decision"] == "deny"
        or risk_result.recommended_decision == "deny"
    ):
        predicted_outcome = "blocked"
    elif (
        policy_result["decision"] == "require_approval"
        or risk_result.recommended_decision == "require_approval"
    ):
        predicted_outcome = "require_approval"

    return {
        "simulation": True,
        "label": "DEMO / SYNTHETIC DATA",
        "identity": {"valid": identity_result.valid, "reasons": identity_result.reasons},
        "capability": {
            "permitted": permission_result.permitted,
            "reasons": permission_result.reasons,
            "missing_capabilities": permission_result.missing_capabilities,
        },
        "policy": policy_result,
        "risk": risk_result.model_dump(),
        "predicted_outcome": predicted_outcome,
        "agent": agent.name,
        "action": request.action,
    }
