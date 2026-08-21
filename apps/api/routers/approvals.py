"""Approval endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apps.api.auth.dependencies import AuthenticatedActor, require_operator
from apps.api.state import state
from core.models.action import ActionStatus

router = APIRouter()


class ApprovalDecision(BaseModel):
    reason: str = ""


@router.get("")
async def list_pending_approvals(actor: AuthenticatedActor = Depends(require_operator)):
    approvals = state.lifecycle.get_pending_approvals()
    return {
        "approvals": approvals,
        "total": len(approvals),
        "demo_mode": state.demo_mode,
        "actor": actor.agent.id,
    }


@router.get("/{action_id}")
async def get_approval(action_id: str, actor: AuthenticatedActor = Depends(require_operator)):
    approval = state.lifecycle.get_approval(action_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return {"approval": approval, "demo_mode": state.demo_mode, "actor": actor.agent.id}


@router.post("/{action_id}/approve")
async def approve_action(
    action_id: str,
    decision: ApprovalDecision | None = None,
    actor: AuthenticatedActor = Depends(require_operator),
):
    pending = state.lifecycle.get_approval(action_id)
    if not pending or pending.status != ActionStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=404, detail="Approval not found or already decided")

    approver_id = actor.agent.id
    result = await state.lifecycle.approve(action_id, approver=approver_id)
    if not result:
        raise HTTPException(status_code=404, detail="Approval not found")
    state.save_action(result, approval_status="approved", approval_actor=approver_id)
    return {
        "action": result,
        "demo_mode": state.demo_mode,
        "approved_by": approver_id,
        "reason": decision.reason if decision else "",
    }


@router.post("/{action_id}/deny")
async def deny_action(
    action_id: str,
    decision: ApprovalDecision | None = None,
    actor: AuthenticatedActor = Depends(require_operator),
):
    pending = state.lifecycle.get_approval(action_id)
    if not pending or pending.status != ActionStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=404, detail="Approval not found or already decided")

    denier_id = actor.agent.id
    reason = decision.reason if decision else ""
    result = await state.lifecycle.deny(action_id, denier=denier_id, reason=reason)
    if not result:
        raise HTTPException(status_code=404, detail="Approval not found")
    state.save_action(
        result,
        approval_status="rejected",
        approval_actor=denier_id,
        approval_reason=reason,
    )
    return {
        "action": result,
        "demo_mode": state.demo_mode,
        "denied_by": denier_id,
        "reason": reason,
    }
