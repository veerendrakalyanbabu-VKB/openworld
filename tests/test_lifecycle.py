"""End-to-end trust pipeline lifecycle tests."""

import pytest

from core.audit.logger import AuditLogger
from core.demo.scenarios import SCENARIO_ALLOW, SCENARIO_DENY, SCENARIO_REQUIRE_APPROVAL
from core.demo.seed import DEMO_AGENTS, DEMO_POLICIES
from core.execution.engine import ExecutionEngine
from core.execution.lifecycle import ActionLifecycle
from core.identity.validator import IdentityValidator
from core.models.action import ActionStatus
from core.models.audit import AuditEventType
from core.permissions.validator import PermissionValidator
from core.policies.engine import PolicyEngine
from core.risk.engine import RiskEngine
from core.verification.engine import VerificationEngine


def _agents_dict():
    return {a.id: a for a in DEMO_AGENTS}


def _make_lifecycle():
    audit = AuditLogger()
    policy_engine = PolicyEngine(DEMO_POLICIES)
    return ActionLifecycle(
        policy_engine=policy_engine,
        risk_engine=RiskEngine(),
        execution_engine=ExecutionEngine(),
        verification_engine=VerificationEngine(),
        audit_logger=audit,
        identity_validator=IdentityValidator(),
        permission_validator=PermissionValidator(),
        agent_resolver=lambda aid: _agents_dict().get(aid),
    ), audit


class TestLifecycleAllow:
    @pytest.mark.asyncio
    async def test_allow_scenario_full_pipeline(self):
        lifecycle, audit = _make_lifecycle()
        agent = _agents_dict()[SCENARIO_ALLOW.agent_id]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action=SCENARIO_ALLOW.action,
            target=SCENARIO_ALLOW.target,
            parameters=SCENARIO_ALLOW.parameters,
        )
        result = await lifecycle.process(action, agent=agent, auto_approve=True)

        assert result.status == ActionStatus.VERIFIED
        stages = [s.stage.value for s in result.stages]
        assert "identity" in stages
        assert "policy" in stages
        assert "risk" in stages
        assert "execution" in stages
        assert "verification" in stages
        assert result.policy_decision is not None
        assert result.policy_decision.decision.value == "allow"

        events = audit.get_events()
        event_types = [e.event_type for e in events]
        assert AuditEventType.ACTION_REQUESTED in event_types
        assert AuditEventType.POLICY_EVALUATED in event_types
        assert AuditEventType.RISK_ASSESSED in event_types
        assert AuditEventType.ACTION_EXECUTED in event_types
        assert AuditEventType.VERIFICATION_COMPLETED in event_types


class TestLifecycleDeny:
    @pytest.mark.asyncio
    async def test_deny_scenario_policy_block(self):
        lifecycle, audit = _make_lifecycle()
        agent = _agents_dict()[SCENARIO_DENY.agent_id]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action=SCENARIO_DENY.action,
            parameters=SCENARIO_DENY.parameters,
        )
        result = await lifecycle.process(action, agent=agent)

        assert result.status == ActionStatus.BLOCKED
        assert result.policy_decision.decision.value == "deny"
        stage_statuses = {s.stage.value: s.status for s in result.stages}
        assert "execution" not in stage_statuses

        blocked_events = [e for e in audit.get_events() if e.event_type == AuditEventType.ACTION_BLOCKED]
        assert len(blocked_events) >= 1
        assert blocked_events[0].decision == "deny"

    @pytest.mark.asyncio
    async def test_deny_suspended_agent_identity(self):
        lifecycle, audit = _make_lifecycle()
        agent = _agents_dict()["agent-data-bot"]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action="database.write",
            parameters={"table": "users"},
        )
        result = await lifecycle.process(action, agent=agent)

        assert result.status == ActionStatus.BLOCKED
        identity_stage = next(s for s in result.stages if s.stage.value == "identity")
        assert identity_stage.status == "failed"
        assert "execution" not in [s.stage.value for s in result.stages if s.stage.value == "execution"]

    @pytest.mark.asyncio
    async def test_deny_missing_capability(self):
        lifecycle, _audit = _make_lifecycle()
        agent = _agents_dict()["agent-email-bot"]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action="payment.create",
            parameters={"amount": 1000},
        )
        result = await lifecycle.process(action, agent=agent)

        assert result.status == ActionStatus.BLOCKED
        assert "execution" not in [s.stage.value for s in result.stages]


class TestLifecycleRequireApproval:
    @pytest.mark.asyncio
    async def test_require_approval_blocks_execution(self):
        lifecycle, audit = _make_lifecycle()
        agent = _agents_dict()[SCENARIO_REQUIRE_APPROVAL.agent_id]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action=SCENARIO_REQUIRE_APPROVAL.action,
            parameters=SCENARIO_REQUIRE_APPROVAL.parameters,
        )
        result = await lifecycle.process(action, agent=agent)

        assert result.status == ActionStatus.PENDING_APPROVAL
        assert "execution" not in [s.stage.value for s in result.stages]

        approval_events = [e for e in audit.get_events() if e.event_type == AuditEventType.APPROVAL_REQUESTED]
        assert len(approval_events) == 1

    @pytest.mark.asyncio
    async def test_approve_permits_execution(self):
        lifecycle, audit = _make_lifecycle()
        agent = _agents_dict()[SCENARIO_REQUIRE_APPROVAL.agent_id]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action=SCENARIO_REQUIRE_APPROVAL.action,
            parameters=SCENARIO_REQUIRE_APPROVAL.parameters,
        )
        pending = await lifecycle.process(action, agent=agent)
        assert pending.status == ActionStatus.PENDING_APPROVAL

        approved = await lifecycle.approve(pending.id, approver="human")
        assert approved.status == ActionStatus.VERIFIED
        assert "execution" in [s.stage.value for s in approved.stages]

        granted = [e for e in audit.get_events() if e.event_type == AuditEventType.APPROVAL_GRANTED]
        assert len(granted) == 1

    @pytest.mark.asyncio
    async def test_reject_blocks_execution(self):
        lifecycle, audit = _make_lifecycle()
        agent = _agents_dict()[SCENARIO_REQUIRE_APPROVAL.agent_id]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action=SCENARIO_REQUIRE_APPROVAL.action,
            parameters=SCENARIO_REQUIRE_APPROVAL.parameters,
        )
        pending = await lifecycle.process(action, agent=agent)

        denied = await lifecycle.deny(pending.id, denier="human", reason="Too risky")
        assert denied.status == ActionStatus.DENIED
        assert "execution" not in [s.stage.value for s in denied.stages]

        denied_events = [e for e in audit.get_events() if e.event_type == AuditEventType.APPROVAL_DENIED]
        assert len(denied_events) == 1
        assert denied_events[0].details.get("reason") == "Too risky"


class TestExecutionSafety:
    @pytest.mark.asyncio
    async def test_no_execution_on_policy_deny(self):
        lifecycle, _ = _make_lifecycle()
        agent = _agents_dict()["agent-finance-bot"]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action="payment.create",
            parameters={"amount": 600000},
        )
        result = await lifecycle.process(action, agent=agent)
        assert result.status == ActionStatus.BLOCKED
        exec_stages = [s for s in result.stages if s.stage.value == "execution"]
        assert len(exec_stages) == 0

    @pytest.mark.asyncio
    async def test_no_execution_on_pending_approval(self):
        lifecycle, _ = _make_lifecycle()
        agent = _agents_dict()["agent-finance-bot"]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action="payment.create",
            parameters={"amount": 75000},
        )
        result = await lifecycle.process(action, agent=agent)
        assert result.status == ActionStatus.PENDING_APPROVAL
        exec_stages = [s for s in result.stages if s.stage.value == "execution"]
        assert len(exec_stages) == 0

    @pytest.mark.asyncio
    async def test_unknown_agent_blocked(self):
        lifecycle, _ = _make_lifecycle()
        action = lifecycle.create_action(
            agent_id="unknown-agent",
            agent_name="Unknown",
            action="email.send",
        )
        result = await lifecycle.process(action, agent=None)
        assert result.status == ActionStatus.BLOCKED


class TestVerification:
    @pytest.mark.asyncio
    async def test_successful_verification(self):
        lifecycle, _ = _make_lifecycle()
        agent = _agents_dict()["agent-email-bot"]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action="email.send",
            parameters={"to": "test@example.com"},
        )
        result = await lifecycle.process(action, agent=agent, auto_approve=True)
        assert result.status == ActionStatus.VERIFIED
        assert result.verification_id is not None

    @pytest.mark.asyncio
    async def test_missing_capability_blocks_before_execution(self):
        lifecycle, _ = _make_lifecycle()
        agent = _agents_dict()["agent-api-bot"]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action="database.write",
            parameters={"table": "users"},
        )
        result = await lifecycle.process(action, agent=agent, auto_approve=True)
        assert result.status == ActionStatus.BLOCKED
        assert "execution" not in [s.stage.value for s in result.stages]
