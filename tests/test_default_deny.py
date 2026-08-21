"""Default-deny policy behavior tests."""

import pytest

from core.audit.logger import AuditLogger
from core.demo.seed import DEMO_POLICIES
from core.execution.engine import ExecutionEngine
from core.execution.lifecycle import ActionLifecycle
from core.models.action import PolicyDecisionType
from core.policies.engine import PolicyEngine
from core.risk.engine import RiskEngine
from core.verification.engine import VerificationEngine


def _make_lifecycle(default_deny: bool) -> ActionLifecycle:
    return ActionLifecycle(
        policy_engine=PolicyEngine(DEMO_POLICIES, default_deny=default_deny),
        risk_engine=RiskEngine(),
        execution_engine=ExecutionEngine(),
        verification_engine=VerificationEngine(),
        audit_logger=AuditLogger(),
    )


class TestDefaultDeny:
    def test_unmatched_policy_denies_in_production_mode(self):
        lifecycle = _make_lifecycle(default_deny=True)
        action = lifecycle.create_action(
            agent_id="agent-email-bot",
            agent_name="EmailBot",
            action="totally.unknown.action",
        )
        decision = lifecycle.policy_engine.evaluate(action, "EmailBot")
        assert decision.decision == PolicyDecisionType.DENY
        assert "default deny" in decision.reasons[0].lower()

    def test_unmatched_policy_allows_in_demo_mode(self):
        lifecycle = _make_lifecycle(default_deny=False)
        action = lifecycle.create_action(
            agent_id="agent-email-bot",
            agent_name="EmailBot",
            action="totally.unknown.action",
        )
        decision = lifecycle.policy_engine.evaluate(action, "EmailBot")
        assert decision.decision == PolicyDecisionType.ALLOW

    def test_matching_allow_still_works(self):
        lifecycle = _make_lifecycle(default_deny=True)
        action = lifecycle.create_action(
            agent_id="agent-email-bot",
            agent_name="EmailBot",
            action="email.send",
            parameters={"to": "test@example.com"},
        )
        decision = lifecycle.policy_engine.evaluate(action, "EmailBot")
        assert decision.decision == PolicyDecisionType.ALLOW

    def test_matching_deny_still_works(self):
        lifecycle = _make_lifecycle(default_deny=True)
        action = lifecycle.create_action(
            agent_id="agent-finance-bot",
            agent_name="FinanceBot",
            action="payment.create",
            parameters={"amount": 600000},
        )
        decision = lifecycle.policy_engine.evaluate(action, "FinanceBot")
        assert decision.decision == PolicyDecisionType.DENY

    def test_matching_approval_still_works(self):
        lifecycle = _make_lifecycle(default_deny=True)
        action = lifecycle.create_action(
            agent_id="agent-finance-bot",
            agent_name="FinanceBot",
            action="payment.create",
            parameters={"amount": 75000},
        )
        decision = lifecycle.policy_engine.evaluate(action, "FinanceBot")
        assert decision.decision == PolicyDecisionType.REQUIRE_APPROVAL


@pytest.mark.asyncio
async def test_production_default_deny_via_api():
    from httpx import ASGITransport, AsyncClient

    from apps.api.config import settings
    from apps.api.main import app
    from apps.api.state import state
    from tests.conftest import action_headers

    settings.demo_mode = False
    state.demo_mode = False
    state.policy_engine.set_default_deny(True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        agents = (await client.get("/api/v1/agents")).json()["agents"]
        email_bot = next(a for a in agents if a["name"] == "EmailBot")
        response = await client.post(
            "/api/v1/actions",
            json={"action": "totally.unknown.action", "parameters": {}},
            headers=action_headers(email_bot["id"]),
        )
        assert response.status_code == 200
        assert response.json()["action"]["status"] == "blocked"
