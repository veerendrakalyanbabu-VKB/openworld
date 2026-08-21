"""MVP scenario tests: allow, approval, deny, verification failure, unknown agent, bypass."""

import pytest

from core.audit.logger import AuditLogger
from core.demo.scenarios import SCENARIO_ALLOW, SCENARIO_DENY, SCENARIO_REQUIRE_APPROVAL
from core.demo.seed import DEMO_AGENTS, DEMO_POLICIES
from core.execution.engine import ActionExecutor, ExecutionBypassError, ExecutionEngine, ExecutionResult
from core.execution.lifecycle import ActionLifecycle
from core.identity.validator import IdentityValidator
from core.models.action import ActionRequest, ActionStatus
from core.models.agent import Agent, AgentStatus, TrustDimensions
from core.models.audit import AuditEventType
from core.permissions.validator import PermissionValidator
from core.policies.engine import PolicyEngine
from core.risk.engine import RiskEngine
from core.verification.engine import VerificationEngine


def _agents():
    return {a.id: a for a in DEMO_AGENTS}


def _lifecycle(engine: ExecutionEngine | None = None):
    audit = AuditLogger()
    execution = engine or ExecutionEngine()
    lifecycle = ActionLifecycle(
        policy_engine=PolicyEngine(DEMO_POLICIES),
        risk_engine=RiskEngine(),
        execution_engine=execution,
        verification_engine=VerificationEngine(),
        audit_logger=audit,
        identity_validator=IdentityValidator(),
        permission_validator=PermissionValidator(),
        agent_resolver=lambda aid: _agents().get(aid),
    )
    return lifecycle, execution, audit


class FailingStatusExecutor(ActionExecutor):
    @property
    def name(self) -> str:
        return "mock_failing_status"

    @property
    def supported_actions(self) -> list[str]:
        return ["test.fail"]

    async def execute(self, action: ActionRequest) -> ExecutionResult:
        return ExecutionResult(success=True, output={"status": "failed", "demo": True}, executor=self.name)


@pytest.mark.asyncio
async def test_scenario_low_risk_allow_execute_verify_audit():
    lifecycle, engine, audit = _lifecycle()
    agent = _agents()[SCENARIO_ALLOW.agent_id]
    action = lifecycle.create_action(
        agent_id=agent.id,
        agent_name=agent.name,
        action="send_email",
        target=SCENARIO_ALLOW.target,
        parameters=SCENARIO_ALLOW.parameters,
    )
    assert action.action == "email.send"
    result = await lifecycle.process(action, agent=agent, auto_approve=True)
    assert result.status == ActionStatus.VERIFIED
    assert engine.execution_count == 1
    stages = [s.stage.value for s in result.stages]
    assert "identity" in stages
    assert "capability" in stages
    assert "policy" in stages
    assert "risk" in stages
    assert "decision" in stages
    assert "execution" in stages
    assert "verification" in stages
    events = {e.event_type for e in audit.get_events()}
    assert AuditEventType.ACTION_EXECUTED in events
    assert AuditEventType.VERIFICATION_COMPLETED in events


@pytest.mark.asyncio
async def test_scenario_medium_risk_requires_approval_then_success():
    lifecycle, engine, audit = _lifecycle()
    agent = _agents()[SCENARIO_REQUIRE_APPROVAL.agent_id]
    action = lifecycle.create_action(
        agent_id=agent.id,
        agent_name=agent.name,
        action=SCENARIO_REQUIRE_APPROVAL.action,
        parameters=SCENARIO_REQUIRE_APPROVAL.parameters,
    )
    pending = await lifecycle.process(action, agent=agent)
    assert pending.status == ActionStatus.PENDING_APPROVAL
    assert engine.execution_count == 0
    approved = await lifecycle.approve(pending.id, approver="ops-human")
    assert approved.status == ActionStatus.VERIFIED
    assert engine.execution_count == 1
    granted = [e for e in audit.get_events() if e.event_type == AuditEventType.APPROVAL_GRANTED]
    assert granted[0].actor == "ops-human"


@pytest.mark.asyncio
async def test_scenario_denied_never_executes():
    lifecycle, engine, audit = _lifecycle()
    agent = _agents()[SCENARIO_DENY.agent_id]
    action = lifecycle.create_action(
        agent_id=agent.id,
        agent_name=agent.name,
        action=SCENARIO_DENY.action,
        parameters=SCENARIO_DENY.parameters,
    )
    result = await lifecycle.process(action, agent=agent)
    assert result.status == ActionStatus.BLOCKED
    assert engine.execution_count == 0
    assert any(e.event_type == AuditEventType.ACTION_BLOCKED for e in audit.get_events())


@pytest.mark.asyncio
async def test_scenario_verification_failure():
    engine = ExecutionEngine()
    engine._executors.clear()
    engine.register(FailingStatusExecutor())
    lifecycle, _, audit = _lifecycle(engine)
    agent = Agent(
        id="agent-test-fail",
        name="FailBot",
        status=AgentStatus.ACTIVE,
        capabilities=["test.fail"],
        trust_dimensions=TrustDimensions(
            identity=100, policy=100, reliability=100, verification=100, violations=100
        ),
    )
    action = lifecycle.create_action(agent_id=agent.id, agent_name=agent.name, action="test.fail")
    result = await lifecycle.process(action, agent=agent, auto_approve=True)
    assert result.status == ActionStatus.VERIFICATION_FAILED
    verification = next(s for s in result.stages if s.stage.value == "verification")
    assert verification.status == "failed"
    assert any(e.event_type == AuditEventType.VERIFICATION_COMPLETED for e in audit.get_events())


@pytest.mark.asyncio
async def test_scenario_unknown_agent_rejected():
    lifecycle, engine, _ = _lifecycle()
    action = lifecycle.create_action(agent_id="unknown-agent", agent_name="Unknown", action="email.send")
    result = await lifecycle.process(action, agent=None)
    assert result.status == ActionStatus.BLOCKED
    assert engine.execution_count == 0


@pytest.mark.asyncio
async def test_scenario_direct_execution_bypass_rejected():
    engine = ExecutionEngine()
    action = ActionRequest(id="bypass", agent_id="agent-email-bot", action="email.send")
    with pytest.raises(ExecutionBypassError):
        await engine.execute(action)
    assert engine.execution_count == 0
