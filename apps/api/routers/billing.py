"""Billing catalog and account endpoints. Plan changes require SYSTEM_ADMIN."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from apps.api.auth.dependencies import AuthenticatedActor, get_authenticated_actor, require_system_admin
from apps.api.state import state
from core.billing.catalog import PLAN_CATALOG, public_catalog
from core.models.audit import AuditEventType

router = APIRouter()


class PlanChangeRequest(BaseModel):
    plan_id: str = Field(..., min_length=1, max_length=32)


@router.get("/catalog")
async def billing_catalog():
    return {
        "catalog": public_catalog(),
        "payments": "BILLING-READY",
        "live": False,
        "pricing": None,
    }


@router.get("/account")
async def billing_account(actor: AuthenticatedActor = Depends(get_authenticated_actor)):
    snapshot = state.billing.snapshot()
    snapshot["actor_id"] = actor.agent.id
    return snapshot


@router.post("/plan")
async def change_plan(
    body: PlanChangeRequest,
    actor: AuthenticatedActor = Depends(require_system_admin),
):
    if body.plan_id not in PLAN_CATALOG:
        raise HTTPException(status_code=400, detail="Unknown plan_id")
    result = state.billing.set_plan(body.plan_id, actor_id=actor.agent.id)
    state.audit_logger.log(
        event_type=AuditEventType.PLAN_CHANGED,
        actor=actor.agent.id,
        subject=result.get("plan_id", body.plan_id),
        action="billing.plan.change",
        decision="changed",
        details={"plan_id": body.plan_id, "entitlements": result["entitlements"]},
    )
    return {**result, "payments": "BILLING-READY", "live": False}


@router.post("/checkout")
async def checkout(actor: AuthenticatedActor = Depends(get_authenticated_actor)):
    """Placeholder. Does not create a real subscription or charge."""
    return state.billing.provider.create_subscription("acct-default", "pro")
