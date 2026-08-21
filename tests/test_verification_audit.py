"""Verification failure and audit evidence tests."""

import pytest

from core.audit.logger import AuditLogger
from core.demo.seed import DEMO_AGENTS, DEMO_POLICIES
from core.execution.engine import ActionExecutor, ExecutionEngine, ExecutionResult
from core.execution.lifecycle import ActionLifecycle
from core.identity.validator import IdentityValidator
from core.models.action import ActionRequest, ActionStatus
from core.models.audit import AuditEventType
from core.permissions.validator import PermissionValidator
from core.policies.engine import PolicyEngine
from core.risk.engine import RiskEngine
from core.verification.engine import VerificationEngine


class FailingStatusExecutor(ActionExecutor):
    """Returns success=True but output status=failed to trigger verification failure."""

    @property
    def name(self) -> str:
        return "mock_failing_status"

    @property
    def supported_actions(self) -> list[str]:
        return ["test.fail"]

    async def execute(self, action: ActionRequest) -> ExecutionResult:
        return ExecutionResult(
            success=True,
            output={"status": "failed", "demo": True},
            executor=self.name,
        )


def _make_lifecycle_with_failing_executor():
    engine = ExecutionEngine()
    engine._executors.clear()
    engine.register(FailingStatusExecutor())
    audit = AuditLogger()
    lifecycle = ActionLifecycle(
        policy_engine=PolicyEngine(DEMO_POLICIES),
        risk_engine=RiskEngine(),
        execution_engine=engine,
        verification_engine=VerificationEngine(),
        audit_logger=audit,
        identity_validator=IdentityValidator(),
        permission_validator=PermissionValidator(),
    )
    return lifecycle, audit


class TestVerificationFailure:
    @pytest.mark.asyncio
    async def test_failed_verification_on_bad_output(self):
        from core.models.agent import Agent, AgentStatus, TrustDimensions

        lifecycle, audit = _make_lifecycle_with_failing_executor()
        agent = Agent(
            id="agent-test",
            name="TestBot",
            status=AgentStatus.ACTIVE,
            capabilities=["test.fail"],
            trust_dimensions=TrustDimensions(
                identity=100, policy=100, reliability=100, verification=100, violations=100
            ),
        )
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action="test.fail",
        )
        result = await lifecycle.process(action, agent=agent, auto_approve=True)
        assert result.status == ActionStatus.EXECUTED
        verification_stage = next(s for s in result.stages if s.stage.value == "verification")
        assert verification_stage.status == "failed"

        verify_events = [
            e for e in audit.get_events()
            if e.event_type == AuditEventType.VERIFICATION_COMPLETED
        ]
        assert len(verify_events) == 1
        assert verify_events[0].decision == "failed"


class TestAuditEvidence:
    @pytest.mark.asyncio
    async def test_allow_audit_contains_required_fields(self):
        from core.demo.scenarios import SCENARIO_ALLOW

        audit = AuditLogger()
        agents = {a.id: a for a in DEMO_AGENTS}
        lifecycle = ActionLifecycle(
            policy_engine=PolicyEngine(DEMO_POLICIES),
            risk_engine=RiskEngine(),
            execution_engine=ExecutionEngine(),
            verification_engine=VerificationEngine(),
            audit_logger=audit,
            identity_validator=IdentityValidator(),
            permission_validator=PermissionValidator(),
            agent_resolver=lambda aid: agents.get(aid),
        )
        agent = agents[SCENARIO_ALLOW.agent_id]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action=SCENARIO_ALLOW.action,
            parameters=SCENARIO_ALLOW.parameters,
        )
        result = await lifecycle.process(action, agent=agent, auto_approve=True)

        events = audit.get_events(correlation_id=result.correlation_id)
        assert len(events) >= 4
        for event in events:
            assert event.correlation_id == result.correlation_id
            assert event.details.get("agent_id") == agent.id
            assert event.timestamp is not None

        event_types = {e.event_type for e in events}
        assert AuditEventType.ACTION_REQUESTED in event_types
        assert AuditEventType.POLICY_EVALUATED in event_types
        assert AuditEventType.ACTION_EXECUTED in event_types

    @pytest.mark.asyncio
    async def test_deny_audit_contains_reason(self):
        from core.demo.scenarios import SCENARIO_DENY

        audit = AuditLogger()
        agents = {a.id: a for a in DEMO_AGENTS}
        lifecycle = ActionLifecycle(
            policy_engine=PolicyEngine(DEMO_POLICIES),
            risk_engine=RiskEngine(),
            execution_engine=ExecutionEngine(),
            verification_engine=VerificationEngine(),
            audit_logger=audit,
            identity_validator=IdentityValidator(),
            permission_validator=PermissionValidator(),
            agent_resolver=lambda aid: agents.get(aid),
        )
        agent = agents[SCENARIO_DENY.agent_id]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action=SCENARIO_DENY.action,
            parameters=SCENARIO_DENY.parameters,
        )
        result = await lifecycle.process(action, agent=agent)

        blocked = [
            e for e in audit.get_events(correlation_id=result.correlation_id)
            if e.event_type == AuditEventType.ACTION_BLOCKED
        ]
        assert len(blocked) >= 1
        assert blocked[0].decision == "deny"
        assert blocked[0].details.get("final_outcome") == "blocked"

    @pytest.mark.asyncio
    async def test_rejection_audit_evidence(self):
        from core.demo.scenarios import SCENARIO_REQUIRE_APPROVAL

        audit = AuditLogger()
        agents = {a.id: a for a in DEMO_AGENTS}
        lifecycle = ActionLifecycle(
            policy_engine=PolicyEngine(DEMO_POLICIES),
            risk_engine=RiskEngine(),
            execution_engine=ExecutionEngine(),
            verification_engine=VerificationEngine(),
            audit_logger=audit,
            identity_validator=IdentityValidator(),
            permission_validator=PermissionValidator(),
            agent_resolver=lambda aid: agents.get(aid),
        )
        agent = agents[SCENARIO_REQUIRE_APPROVAL.agent_id]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action=SCENARIO_REQUIRE_APPROVAL.action,
            parameters=SCENARIO_REQUIRE_APPROVAL.parameters,
        )
        pending = await lifecycle.process(action, agent=agent)
        await lifecycle.deny(pending.id, reason="Not authorized")

        denied_events = [
            e for e in audit.get_events(correlation_id=pending.correlation_id)
            if e.event_type == AuditEventType.APPROVAL_DENIED
        ]
        assert len(denied_events) == 1
        assert denied_events[0].details.get("reason") == "Not authorized"
