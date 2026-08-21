"""Identity validation tests."""

from core.demo.seed import DEMO_AGENTS
from core.identity.validator import IdentityValidator
from core.models.agent import Agent, AgentStatus, TrustDimensions


class TestIdentityValidator:
    def setup_method(self):
        self.validator = IdentityValidator()
        self.active_agent = next(a for a in DEMO_AGENTS if a.name == "FinanceBot")
        self.suspended_agent = next(a for a in DEMO_AGENTS if a.name == "DataBot")

    def test_valid_active_agent(self):
        result = self.validator.validate(self.active_agent)
        assert result.valid is True
        assert len(result.reasons) > 0

    def test_invalid_suspended_agent(self):
        result = self.validator.validate(self.suspended_agent)
        assert result.valid is False
        assert "suspended" in result.reasons[0].lower()

    def test_invalid_inactive_agent(self):
        agent = Agent(
            id="test-inactive",
            name="InactiveBot",
            status=AgentStatus.INACTIVE,
            capabilities=["email.send"],
            trust_dimensions=TrustDimensions(
                identity=100, policy=100, reliability=100, verification=100, violations=100
            ),
        )
        result = self.validator.validate(agent)
        assert result.valid is False
        assert "inactive" in result.reasons[0].lower()

    def test_invalid_pending_agent(self):
        agent = Agent(
            id="test-pending",
            name="PendingBot",
            status=AgentStatus.PENDING,
            capabilities=["email.send"],
            trust_dimensions=TrustDimensions(
                identity=100, policy=100, reliability=100, verification=100, violations=100
            ),
        )
        result = self.validator.validate(agent)
        assert result.valid is False
        assert "pending" in result.reasons[0].lower()
