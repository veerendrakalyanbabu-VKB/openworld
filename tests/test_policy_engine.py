"""Policy engine tests."""

from core.audit.logger import AuditLogger
from core.demo.seed import DEMO_POLICIES
from core.execution.engine import ExecutionEngine
from core.execution.lifecycle import ActionLifecycle
from core.models.action import PolicyDecisionType
from core.policies.engine import PolicyEngine
from core.risk.engine import RiskEngine
from core.verification.engine import VerificationEngine


def _make_lifecycle():
    audit = AuditLogger()
    policy_engine = PolicyEngine(DEMO_POLICIES)
    return ActionLifecycle(
        policy_engine=policy_engine,
        risk_engine=RiskEngine(),
        execution_engine=ExecutionEngine(),
        verification_engine=VerificationEngine(),
        audit_logger=audit,
    )


class TestPolicyEngine:
    def test_large_payment_requires_approval(self):
        engine = PolicyEngine(DEMO_POLICIES)
        lifecycle = _make_lifecycle()
        action = lifecycle.create_action(
            agent_id="agent-finance-bot",
            agent_name="FinanceBot",
            action="payment.create",
            parameters={"amount": 60000},
        )
        decision = engine.evaluate(action, "FinanceBot")
        assert decision.decision == PolicyDecisionType.REQUIRE_APPROVAL

    def test_small_payment_allowed(self):
        engine = PolicyEngine(DEMO_POLICIES)
        lifecycle = _make_lifecycle()
        action = lifecycle.create_action(
            agent_id="agent-finance-bot",
            agent_name="FinanceBot",
            action="payment.create",
            parameters={"amount": 5000},
        )
        decision = engine.evaluate(action, "FinanceBot")
        assert decision.decision == PolicyDecisionType.ALLOW

    def test_huge_payment_denied(self):
        engine = PolicyEngine(DEMO_POLICIES)
        lifecycle = _make_lifecycle()
        action = lifecycle.create_action(
            agent_id="agent-finance-bot",
            agent_name="FinanceBot",
            action="payment.create",
            parameters={"amount": 600000},
        )
        decision = engine.evaluate(action, "FinanceBot")
        assert decision.decision == PolicyDecisionType.DENY

    def test_databot_write_denied(self):
        engine = PolicyEngine(DEMO_POLICIES)
        lifecycle = _make_lifecycle()
        action = lifecycle.create_action(
            agent_id="agent-data-bot",
            agent_name="DataBot",
            action="database.write",
        )
        decision = engine.evaluate(action, "DataBot")
        assert decision.decision == PolicyDecisionType.DENY

    def test_simulation_returns_result(self):
        engine = PolicyEngine(DEMO_POLICIES)
        lifecycle = _make_lifecycle()
        action = lifecycle.create_action(
            agent_id="agent-finance-bot",
            agent_name="FinanceBot",
            action="payment.create",
            parameters={"amount": 60000},
        )
        result = engine.simulate(action, "FinanceBot")
        assert result["simulation"] is True
        assert result["decision"] == "require_approval"
