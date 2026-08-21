"""Execution sentinel tests — prove executor is not called when gates block."""

import pytest

from core.audit.logger import AuditLogger
from core.demo.scenarios import SCENARIO_ALLOW, SCENARIO_DENY, SCENARIO_REQUIRE_APPROVAL
from core.demo.seed import DEMO_AGENTS, DEMO_POLICIES
from core.execution.engine import ExecutionEngine
from core.execution.lifecycle import ActionLifecycle
from core.identity.validator import IdentityValidator
from core.models.action import ActionStatus
from core.permissions.validator import PermissionValidator
from core.policies.engine import PolicyEngine
from core.risk.engine import RiskEngine
from core.verification.engine import VerificationEngine


def _agents_dict():
    return {a.id: a for a in DEMO_AGENTS}


def _make_lifecycle():
    execution_engine = ExecutionEngine()
    audit = AuditLogger()
    lifecycle = ActionLifecycle(
        policy_engine=PolicyEngine(DEMO_POLICIES),
        risk_engine=RiskEngine(),
        execution_engine=execution_engine,
        verification_engine=VerificationEngine(),
        audit_logger=audit,
        identity_validator=IdentityValidator(),
        permission_validator=PermissionValidator(),
        agent_resolver=lambda aid: _agents_dict().get(aid),
    )
    return lifecycle, execution_engine, audit


class TestExecutionSentinel:
    """Prove execution_count stays 0 when trust gates block."""

    @pytest.mark.asyncio
    async def test_allow_increments_execution_count(self):
        lifecycle, engine, _ = _make_lifecycle()
        agent = _agents_dict()[SCENARIO_ALLOW.agent_id]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action=SCENARIO_ALLOW.action,
            parameters=SCENARIO_ALLOW.parameters,
        )
        await lifecycle.process(action, agent=agent, auto_approve=True)
        assert engine.execution_count == 1

    @pytest.mark.asyncio
    async def test_deny_does_not_call_executor(self):
        lifecycle, engine, _ = _make_lifecycle()
        agent = _agents_dict()[SCENARIO_DENY.agent_id]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action=SCENARIO_DENY.action,
            parameters=SCENARIO_DENY.parameters,
        )
        result = await lifecycle.process(action, agent=agent)
        assert result.status == ActionStatus.BLOCKED
        assert engine.execution_count == 0

    @pytest.mark.asyncio
    async def test_pending_approval_does_not_call_executor(self):
        lifecycle, engine, _ = _make_lifecycle()
        agent = _agents_dict()[SCENARIO_REQUIRE_APPROVAL.agent_id]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action=SCENARIO_REQUIRE_APPROVAL.action,
            parameters=SCENARIO_REQUIRE_APPROVAL.parameters,
        )
        result = await lifecycle.process(action, agent=agent)
        assert result.status == ActionStatus.PENDING_APPROVAL
        assert engine.execution_count == 0

    @pytest.mark.asyncio
    async def test_rejected_approval_does_not_call_executor(self):
        lifecycle, engine, _ = _make_lifecycle()
        agent = _agents_dict()[SCENARIO_REQUIRE_APPROVAL.agent_id]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action=SCENARIO_REQUIRE_APPROVAL.action,
            parameters=SCENARIO_REQUIRE_APPROVAL.parameters,
        )
        pending = await lifecycle.process(action, agent=agent)
        denied = await lifecycle.deny(pending.id, reason="Rejected")
        assert denied.status == ActionStatus.DENIED
        assert engine.execution_count == 0

    @pytest.mark.asyncio
    async def test_approved_then_executes_once(self):
        lifecycle, engine, _ = _make_lifecycle()
        agent = _agents_dict()[SCENARIO_REQUIRE_APPROVAL.agent_id]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action=SCENARIO_REQUIRE_APPROVAL.action,
            parameters=SCENARIO_REQUIRE_APPROVAL.parameters,
        )
        pending = await lifecycle.process(action, agent=agent)
        assert engine.execution_count == 0
        approved = await lifecycle.approve(pending.id)
        assert approved.status == ActionStatus.VERIFIED
        assert engine.execution_count == 1

    @pytest.mark.asyncio
    async def test_invalid_identity_does_not_call_executor(self):
        lifecycle, engine, _ = _make_lifecycle()
        agent = _agents_dict()["agent-data-bot"]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action="database.write",
            parameters={"table": "users"},
        )
        result = await lifecycle.process(action, agent=agent)
        assert result.status == ActionStatus.BLOCKED
        assert engine.execution_count == 0

    @pytest.mark.asyncio
    async def test_missing_capability_does_not_call_executor(self):
        lifecycle, engine, _ = _make_lifecycle()
        agent = _agents_dict()["agent-email-bot"]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action="payment.create",
            parameters={"amount": 1000},
        )
        result = await lifecycle.process(action, agent=agent, auto_approve=True)
        assert result.status == ActionStatus.BLOCKED
        assert engine.execution_count == 0
