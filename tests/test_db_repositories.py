"""Repository-layer persistence tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.main import app
from apps.api.state import state
from core.audit.logger import AuditLogger
from core.db.repositories import (
    ActionRepository,
    AgentRepository,
    AuditRepository,
    PolicyRepository,
)
from core.db.session import session_scope
from core.demo.seed import DEMO_AGENTS, DEMO_POLICIES
from core.execution.engine import ExecutionEngine
from core.execution.lifecycle import ActionLifecycle
from core.models.audit import AuditEvent, AuditEventType
from core.risk.engine import RiskEngine
from core.verification.engine import VerificationEngine
from tests.conftest import action_headers, operator_headers


class TestRepositories:
    def test_agent_save_and_retrieve(self):
        agent = DEMO_AGENTS[0]
        with session_scope() as session:
            saved = AgentRepository(session).save(agent)
            loaded = AgentRepository(session).get(agent.id)
        assert loaded is not None
        assert loaded.id == saved.id
        assert loaded.name == agent.name

    def test_policy_save_and_retrieve(self):
        policy = DEMO_POLICIES[0]
        with session_scope() as session:
            saved = PolicyRepository(session).save(policy)
            loaded = PolicyRepository(session).get(policy.id)
        assert loaded is not None
        assert loaded.id == saved.id
        assert loaded.name == policy.name

    def test_action_save_and_retrieve(self):
        lifecycle = ActionLifecycle(
            policy_engine=state.policy_engine,
            risk_engine=RiskEngine(),
            execution_engine=ExecutionEngine(),
            verification_engine=VerificationEngine(),
            audit_logger=AuditLogger(),
            agent_resolver=state.get_agent,
        )
        agent = state.get_agent(DEMO_AGENTS[0].id)
        assert agent is not None
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action="email.send",
            parameters={"to": "repo@test.com"},
        )
        with session_scope() as session:
            ActionRepository(session).save(action)
            loaded = ActionRepository(session).get(action.id)
        assert loaded is not None
        assert loaded.action == "email.send"
        assert loaded.agent_id == agent.id

    def test_approval_save_update_and_retrieve(self):
        from core.models.action import ActionStatus

        lifecycle = ActionLifecycle(
            policy_engine=state.policy_engine,
            risk_engine=RiskEngine(),
            execution_engine=ExecutionEngine(),
            verification_engine=VerificationEngine(),
            audit_logger=AuditLogger(),
            agent_resolver=state.get_agent,
        )
        agent = state.get_agent(next(a for a in DEMO_AGENTS if a.name == "FinanceBot").id)
        assert agent is not None
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action="payment.create",
            parameters={"amount": 75000},
        )
        action.status = ActionStatus.PENDING_APPROVAL
        with session_scope() as session:
            repo = ActionRepository(session)
            repo.save(action, approval_status="pending")
            pending = repo.list_pending_approvals()
            assert any(a.id == action.id for a in pending)
            action.status = ActionStatus.VERIFIED
            repo.save(action, approval_status="approved", approval_actor="human")
            updated = repo.get(action.id)
        assert updated is not None
        assert updated.status == ActionStatus.VERIFIED

    def test_verification_persisted_on_action(self):
        lifecycle = ActionLifecycle(
            policy_engine=state.policy_engine,
            risk_engine=RiskEngine(),
            execution_engine=ExecutionEngine(),
            verification_engine=VerificationEngine(),
            audit_logger=AuditLogger(),
            agent_resolver=state.get_agent,
        )
        agent = state.get_agent(DEMO_AGENTS[0].id)
        assert agent is not None
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action="email.send",
            parameters={"to": "verify@test.com"},
        )
        action.verification_id = "ver-test-001"
        with session_scope() as session:
            ActionRepository(session).save(action)
            loaded = ActionRepository(session).get(action.id)
        assert loaded is not None
        assert loaded.verification_id == "ver-test-001"

    def test_audit_append_and_retrieve(self):
        event = AuditEvent(
            id="audit-test-001",
            event_type=AuditEventType.ACTION_EXECUTED,
            actor="EmailBot",
            subject="action-test",
            action="email.send",
            decision="allow",
            correlation_id="corr-test",
        )
        with session_scope() as session:
            AuditRepository(session).append(event)
            events = AuditRepository(session).get_events(limit=10)
            count = AuditRepository(session).count()
        assert count >= 1
        assert any(e.id == "audit-test-001" for e in events)


@pytest.mark.asyncio
async def test_restart_persistence_simulation():
    """Simulate API restart: clear caches, re-init, verify records survive."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        agents = (await client.get("/api/v1/agents")).json()["agents"]
        email_bot = next(a for a in agents if a["name"] == "EmailBot")
        finance_bot = next(a for a in agents if a["name"] == "FinanceBot")

        allow_resp = await client.post(
            "/api/v1/actions",
            json={
                "action": "email.send",
                "parameters": {"to": "restart@test.com"},
                "auto_approve": True,
            },
            headers=action_headers(email_bot["id"]),
        )
        allow_id = allow_resp.json()["action"]["id"]

        deny_resp = await client.post(
            "/api/v1/actions",
            json={"action": "payment.create", "parameters": {"amount": 600000}},
            headers=action_headers(finance_bot["id"]),
        )
        deny_id = deny_resp.json()["action"]["id"]

        pending_resp = await client.post(
            "/api/v1/actions",
            json={
                "action": "payment.create",
                "parameters": {"amount": 75000, "recipient": "Restart Vendor"},
            },
            headers=action_headers(finance_bot["id"]),
        )
        pending_id = pending_resp.json()["action"]["id"]
        await client.post(
            f"/api/v1/approvals/{pending_id}/approve",
            headers=operator_headers(),
        )

        audit_before = (await client.get("/api/v1/audit", headers=operator_headers())).json()["total"]

    # Simulate restart
    state._agents.clear()
    state._policies.clear()
    state._actions.clear()
    state.audit_logger._events.clear()
    state.lifecycle.reset()
    state._restore_pending_approvals()
    state.policy_engine.set_policies(state.list_policies())

    assert state.get_agent(email_bot["id"]) is not None
    assert state.get_action(allow_id) is not None
    assert state.get_action(allow_id).status.value == "verified"
    assert state.get_action(deny_id) is not None
    assert state.get_action(deny_id).status.value == "blocked"
    approved = state.get_action(pending_id)
    assert approved is not None
    assert approved.status.value == "verified"
    assert approved.verification_id is not None

    with session_scope() as session:
        audit_after = AuditRepository(session).count()
    assert audit_after >= audit_before
