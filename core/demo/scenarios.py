"""Deterministic canonical trust scenarios for demonstration and testing."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TrustScenario:
    """A deterministic trust pipeline scenario."""

    name: str
    description: str
    agent_id: str
    agent_name: str
    action: str
    parameters: dict
    expected_decision: str
    expected_outcome: str
    target: str = ""


# Scenario A — ALLOW: safe email send by EmailBot
SCENARIO_ALLOW = TrustScenario(
    name="ALLOW",
    description="Safe email action permitted through full pipeline",
    agent_id="agent-email-bot",
    agent_name="EmailBot",
    action="email.send",
    parameters={"to": "user@example.com", "subject": "Welcome"},
    target="user@example.com",
    expected_decision="allow",
    expected_outcome="verified",
)

# Scenario B — DENY: huge payment blocked by policy
SCENARIO_DENY = TrustScenario(
    name="DENY",
    description="Payment over ₹500,000 denied by policy — execution must not occur",
    agent_id="agent-finance-bot",
    agent_name="FinanceBot",
    action="payment.create",
    parameters={"amount": 600000, "recipient": "Vendor Corp"},
    target="vendor@corp.com",
    expected_decision="deny",
    expected_outcome="blocked",
)

# Scenario C — REQUIRE_APPROVAL: large payment needs human approval
SCENARIO_REQUIRE_APPROVAL = TrustScenario(
    name="REQUIRE_APPROVAL",
    description="Payment over ₹50,000 requires human approval before execution",
    agent_id="agent-finance-bot",
    agent_name="FinanceBot",
    action="payment.create",
    parameters={"amount": 75000, "recipient": "ABC Services"},
    target="ABC Services",
    expected_decision="require_approval",
    expected_outcome="pending_approval",
)

# Additional deny scenario: suspended agent capability violation
SCENARIO_DENY_CAPABILITY = TrustScenario(
    name="DENY_CAPABILITY",
    description="DataBot lacks permission for unauthorized action",
    agent_id="agent-data-bot",
    agent_name="DataBot",
    action="database.write",
    parameters={"table": "users"},
    expected_decision="deny",
    expected_outcome="blocked",
)

CANONICAL_SCENARIOS = [SCENARIO_ALLOW, SCENARIO_DENY, SCENARIO_REQUIRE_APPROVAL]
