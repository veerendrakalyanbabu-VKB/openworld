"""Risk engine tests."""

from core.audit.logger import AuditLogger
from core.demo.seed import DEMO_POLICIES
from core.execution.engine import ExecutionEngine
from core.execution.lifecycle import ActionLifecycle
from core.models.risk import RiskLevel
from core.policies.engine import PolicyEngine
from core.risk.engine import RiskEngine
from core.verification.engine import VerificationEngine


def _make_lifecycle():
    return ActionLifecycle(
        policy_engine=PolicyEngine(DEMO_POLICIES),
        risk_engine=RiskEngine(),
        execution_engine=ExecutionEngine(),
        verification_engine=VerificationEngine(),
        audit_logger=AuditLogger(),
    )


class TestRiskEngine:
    def test_low_risk_email(self):
        engine = RiskEngine()
        lifecycle = _make_lifecycle()
        action = lifecycle.create_action(
            agent_id="agent-email-bot",
            agent_name="EmailBot",
            action="email.send",
            parameters={"to": "user@example.com"},
        )
        risk = engine.assess(action)
        assert risk.risk_level == RiskLevel.LOW
        assert risk.risk_score < 30

    def test_high_risk_large_payment(self):
        engine = RiskEngine()
        lifecycle = _make_lifecycle()
        action = lifecycle.create_action(
            agent_id="agent-finance-bot",
            agent_name="FinanceBot",
            action="payment.create",
            parameters={"amount": 100000},
        )
        risk = engine.assess(action)
        assert risk.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.MEDIUM)
        assert len(risk.reasons) > 0

    def test_risk_has_factors(self):
        engine = RiskEngine()
        lifecycle = _make_lifecycle()
        action = lifecycle.create_action(
            agent_id="agent-finance-bot",
            agent_name="FinanceBot",
            action="payment.create",
            parameters={"amount": 50000},
        )
        risk = engine.assess(action)
        assert "action_sensitivity" in risk.factors
        assert risk.recommended_decision in ("allow", "deny", "require_approval")
