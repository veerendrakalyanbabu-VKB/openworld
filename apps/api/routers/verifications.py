"""Verification endpoints."""

from fastapi import APIRouter

from apps.api.state import state

router = APIRouter()


@router.get("")
async def list_verifications():
    verifications = []
    for action in state.list_actions(limit=200):
        if action.verification_id:
            for stage in action.stages:
                if stage.stage.value == "verification":
                    verifications.append({
                        "verification_id": action.verification_id,
                        "action_id": action.id,
                        "agent_name": action.agent_name,
                        "action_type": action.action,
                        "status": stage.status,
                        "details": stage.details,
                        "evidence": stage.evidence,
                    })
    return {"verifications": verifications, "total": len(verifications), "demo_mode": state.demo_mode}
