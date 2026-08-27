"""Regression tests for examples/gateway_quickstart.py."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.main import app
from tests.conftest import action_headers


@pytest.mark.asyncio
async def test_gateway_quickstart_send_email_passes_trust_pipeline():
    """Mirror examples/gateway_quickstart.py: send_email alias → verified sandbox email."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        agents = await client.get("/api/v1/agents")
        assert agents.status_code == 200
        email_bot = next(a for a in agents.json()["agents"] if a["name"] == "EmailBot")
        assert "email.send" in email_bot["capabilities"]

        policies = await client.get("/api/v1/policies")
        assert policies.status_code == 200
        assert any(p["id"] == "policy-email-limits" for p in policies.json()["policies"])

        response = await client.post(
            "/api/v1/actions",
            json={
                "action": "send_email",
                "target": "customer@example.com",
                "parameters": {
                    "to": "customer@example.com",
                    "purpose": "invoice_delivery",
                    "subject": "OpenWorld Gateway MVP",
                },
                "auto_approve": True,
            },
            headers=action_headers(
                "agent-email-bot",
                idempotency_key=f"test-gateway-quickstart-{uuid.uuid4()}",
            ),
        )
        assert response.status_code == 200, response.text
        action = response.json()["action"]

        assert action["action"] == "email.send"
        assert action["status"] == "verified"
        assert action["risk_level"] is not None
        assert action["risk_score"] is not None

        stages = {stage["stage"]: stage["status"] for stage in action["stages"]}
        assert stages["identity"] == "verified"
        assert stages["capability"] == "authorized"
        assert stages["policy"] == "allow"
        assert stages["risk"] in {"low", "medium", "high", "critical"}
        assert stages["execution"] == "completed"
        assert stages["verification"] == "verified"
        assert action["policy_decision"]["policy_id"] == "policy-email-limits"
