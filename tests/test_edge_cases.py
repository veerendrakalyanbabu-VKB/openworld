"""Edge case and failure safety tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_agent_token
from apps.api.main import app
from core.audit.logger import AuditLogger
from core.demo.seed import DEMO_AGENTS, DEMO_POLICIES
from core.execution.engine import ExecutionEngine
from core.execution.lifecycle import ActionLifecycle
from core.identity.validator import IdentityValidator
from core.models.action import ActionStatus
from core.permissions.validator import PermissionValidator
from core.policies.engine import PolicyEngine
from core.risk.engine import RiskEngine
from core.verification.engine import VerificationEngine
from tests.conftest import action_headers, operator_headers


def _make_lifecycle():
    return ActionLifecycle(
        policy_engine=PolicyEngine(DEMO_POLICIES),
        risk_engine=RiskEngine(),
        execution_engine=ExecutionEngine(),
        verification_engine=VerificationEngine(),
        audit_logger=AuditLogger(),
        identity_validator=IdentityValidator(),
        permission_validator=PermissionValidator(),
        agent_resolver=lambda aid: {a.id: a for a in DEMO_AGENTS}.get(aid),
    )


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_unknown_agent_api(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/actions",
                json={"action": "email.send"},
                headers={"Authorization": f"Bearer {create_agent_token('nonexistent')}"},
            )
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_action_missing_fields(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/actions", json={})
            assert response.status_code == 401

            agents = (await client.get("/api/v1/agents")).json()["agents"]
            email_bot = next(a for a in agents if a["name"] == "EmailBot")
            response = await client.post(
                "/api/v1/actions",
                json={},
                headers=action_headers(email_bot["id"]),
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_duplicate_approval_request(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            agents = (await client.get("/api/v1/agents")).json()["agents"]
            finance_bot = next(a for a in agents if a["name"] == "FinanceBot")

            response = await client.post(
                "/api/v1/actions",
                json={
                    "action": "payment.create",
                    "parameters": {"amount": 75000},
                },
                headers=action_headers(finance_bot["id"]),
            )
            action_id = response.json()["action"]["id"]

            approve1 = await client.post(
                f"/api/v1/approvals/{action_id}/approve",
                headers=operator_headers(),
            )
            assert approve1.status_code == 200

            approve2 = await client.post(
                f"/api/v1/approvals/{action_id}/approve",
                headers=operator_headers(),
            )
            assert approve2.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_nonexistent_action(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/approvals/fake-id/approve",
                headers=operator_headers(),
            )
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_deny_nonexistent_action(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/approvals/fake-id/deny",
                headers=operator_headers(),
            )
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_suspended_agent_blocked(self):
        lifecycle = _make_lifecycle()
        agent = next(a for a in DEMO_AGENTS if a.name == "DataBot")
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action="database.write",
            parameters={"table": "analytics"},
        )
        result = await lifecycle.process(action, agent=agent)
        assert result.status == ActionStatus.BLOCKED

    @pytest.mark.asyncio
    async def test_no_executor_fails_safely(self):
        from core.models.agent import Agent, AgentStatus, TrustDimensions

        lifecycle = ActionLifecycle(
            policy_engine=PolicyEngine(DEMO_POLICIES),
            risk_engine=RiskEngine(),
            execution_engine=ExecutionEngine(),
            verification_engine=VerificationEngine(),
            audit_logger=AuditLogger(),
            identity_validator=IdentityValidator(),
            permission_validator=PermissionValidator(),
            agent_resolver=lambda aid: None,
        )
        agent = Agent(
            id="agent-custom",
            name="CustomBot",
            status=AgentStatus.ACTIVE,
            capabilities=["custom.unregistered"],
            trust_dimensions=TrustDimensions(
                identity=100, policy=100, reliability=100, verification=100, violations=100
            ),
        )
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action="custom.unregistered",
        )
        result = await lifecycle.process(action, agent=agent, auto_approve=True)
        assert result.status == ActionStatus.FAILED

    @pytest.mark.asyncio
    async def test_canonical_scenarios_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/scenarios")
            assert response.status_code == 200
            data = response.json()
            names = [s["name"] for s in data["scenarios"]]
            assert "ALLOW" in names
            assert "DENY" in names
            assert "REQUIRE_APPROVAL" in names

    @pytest.mark.asyncio
    async def test_agent_impersonation_rejected(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            agents = (await client.get("/api/v1/agents")).json()["agents"]
            email_bot = next(a for a in agents if a["name"] == "EmailBot")
            finance_bot = next(a for a in agents if a["name"] == "FinanceBot")

            response = await client.post(
                "/api/v1/actions",
                json={
                    "agent_id": finance_bot["id"],
                    "action": "email.send",
                    "parameters": {"to": "test@example.com"},
                    "auto_approve": True,
                },
                headers=action_headers(email_bot["id"]),
            )
            assert response.status_code == 200
            assert response.json()["action"]["agent_id"] == email_bot["id"]
