"""Canonical trust scenario endpoints."""

from fastapi import APIRouter

from core.demo.scenarios import CANONICAL_SCENARIOS

router = APIRouter()


@router.get("/scenarios")
async def list_scenarios():
    return {
        "scenarios": [
            {
                "name": s.name,
                "description": s.description,
                "agent_id": s.agent_id,
                "agent_name": s.agent_name,
                "action": s.action,
                "parameters": s.parameters,
                "target": s.target,
                "expected_decision": s.expected_decision,
                "expected_outcome": s.expected_outcome,
            }
            for s in CANONICAL_SCENARIOS
        ],
        "label": "DEMO / SYNTHETIC DATA",
    }
