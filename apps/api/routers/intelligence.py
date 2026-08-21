"""Intelligence endpoints — evidence-based system queries."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from apps.api.auth.audit_access import intelligence_access_level
from apps.api.auth.dependencies import AuthenticatedActor, get_optional_authenticated_actor
from apps.api.auth.roles import Role, has_any_role
from apps.api.config import settings
from apps.api.state import state

router = APIRouter()


def _public_demo_response(query: str) -> dict:
    return {
        "query": query,
        "answer": "Authentication required for detailed intelligence in production. Demo public overview only.",
        "evidence": {"demo_mode": True, "access": "public"},
        "evidence_based": True,
        "demo_mode": True,
        "label": "DEMO / SYNTHETIC DATA",
        "suggestions": [
            "Why was this action blocked?",
            "Which agents have unusual behavior?",
            "Show me failed verifications.",
        ],
    }


def _filter_actions_for_actor(actions, actor: AuthenticatedActor | None):
    if actor is None:
        return []
    level = intelligence_access_level(actor)
    if level in ("admin", "operator"):
        return actions
    return [a for a in actions if a.agent_id == actor.agent.id]


@router.get("/query")
async def intelligence_query(
    q: str = Query(..., min_length=3),
    actor: AuthenticatedActor | None = Depends(get_optional_authenticated_actor),
):
    """Answer questions using internal system evidence."""
    if not settings.demo_mode and actor is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    if settings.demo_mode and actor is None:
        return _public_demo_response(q)

    query = q.lower()
    access = intelligence_access_level(actor)
    results: dict = {
        "query": q,
        "evidence_based": True,
        "demo_mode": state.demo_mode,
        "access_level": access,
        "actor": actor.agent.id if actor else None,
    }
    if state.demo_mode:
        results["label"] = "DEMO / SYNTHETIC DATA"

    if access == "agent" and any(k in query for k in ("pending", "approval", "unusual", "behavior", "today", "changed")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient authorization for this query")

    if "blocked" in query:
        blocked = [
            a
            for a in _filter_actions_for_actor(state.list_actions(limit=500), actor)
            if a.status.value in ("blocked", "denied")
        ]
        results["answer"] = f"Found {len(blocked)} blocked action(s)."
        results["evidence"] = [
            {
                "action_id": a.id,
                "agent": a.agent_name,
                "action": a.action,
                "status": a.status.value,
                "policy": a.policy_decision.policy_name if a.policy_decision else None,
                "reasons": a.policy_decision.reasons if a.policy_decision else [],
            }
            for a in blocked
        ]

    elif "approval" in query or "pending" in query:
        if access == "agent":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient authorization")
        pending = state.lifecycle.get_pending_approvals()
        results["answer"] = f"There are {len(pending)} action(s) pending approval."
        results["evidence"] = [
            {
                "action_id": a.id,
                "agent": a.agent_name,
                "action": a.action,
                "risk_level": a.risk_level,
                "parameters": a.parameters,
            }
            for a in pending
        ]

    elif "verification" in query and "fail" in query:
        failed = [
            a
            for a in _filter_actions_for_actor(state.list_actions(limit=500), actor)
            if any(s.stage.value == "verification" and s.status == "failed" for s in a.stages)
        ]
        results["answer"] = f"Found {len(failed)} failed verification(s)."
        results["evidence"] = [{"action_id": a.id, "agent": a.agent_name, "action": a.action} for a in failed]

    elif "unusual" in query or "behavior" in query:
        if access == "agent":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient authorization")
        unusual = [a for a in state.list_agents() if a.trust_score < 90 or a.status.value == "suspended"]
        results["answer"] = f"Found {len(unusual)} agent(s) with unusual behavior."
        results["evidence"] = [
            {
                "agent": a.name,
                "trust_score": a.trust_score,
                "status": a.status.value,
                "trust_dimensions": a.trust_dimensions.model_dump(),
            }
            for a in unusual
        ]

    elif "policy" in query and "approval" in query:
        if not has_any_role(actor.roles, Role.POLICY_ADMIN, Role.SYSTEM_ADMIN):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient authorization")
        approval_actions = [
            a
            for a in state.list_actions(limit=500)
            if a.policy_decision and a.policy_decision.decision.value == "require_approval"
        ]
        policy_counts: dict[str, int] = {}
        for a in approval_actions:
            pname = a.policy_decision.policy_name or "unknown"
            policy_counts[pname] = policy_counts.get(pname, 0) + 1
        results["answer"] = "Policy approval frequency analysis."
        results["evidence"] = [{"policy": k, "approval_count": v} for k, v in policy_counts.items()]

    elif "today" in query or "changed" in query:
        if access == "agent":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient authorization")
        actions = sorted(state.list_actions(limit=500), key=lambda a: a.created_at, reverse=True)[:10]
        events = state.audit_logger.get_events(limit=10)
        results["answer"] = f"Recent activity: {len(actions)} actions, {len(events)} audit events."
        results["evidence"] = {
            "recent_actions": [
                {"id": a.id, "agent": a.agent_name, "action": a.action, "status": a.status.value}
                for a in actions
            ],
            "recent_events": [{"type": e.event_type.value, "actor": e.actor, "action": e.action} for e in events],
        }

    else:
        if access == "agent":
            own = state.list_actions(agent_id=actor.agent.id, limit=20)
            results["answer"] = f"Agent overview: {len(own)} recent action(s)."
            results["evidence"] = [
                {"id": a.id, "action": a.action, "status": a.status.value} for a in own
            ]
        else:
            stats = state.get_stats()
            results["answer"] = "System overview based on current evidence."
            results["evidence"] = stats
            results["suggestions"] = [
                "Why was this action blocked?",
                "Which agents have unusual behavior?",
                "Show me failed verifications.",
                "Which policies caused the most approvals?",
                "What changed today?",
            ]

    return results
