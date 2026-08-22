"""Application state with database-backed persistence."""

from collections.abc import Callable

from apps.api.config import settings
from core.audit.logger import AuditLogger
from core.billing.service import BillingService
from core.db.repositories import (
    ActionRepository,
    AgentRepository,
    AuditRepository,
    PolicyRepository,
    PolicyVersionRepository,
)
from core.db.session import create_all_tables, drop_all_tables, init_engine, session_scope
from core.demo.seed import DEMO_AGENTS, DEMO_POLICIES
from core.execution.engine import ExecutionEngine
from core.execution.lifecycle import ActionLifecycle
from core.models.action import ActionRequest
from core.models.agent import Agent
from core.models.audit import AuditEvent
from core.models.policy import Policy
from core.policies.engine import PolicyEngine
from core.risk.engine import RiskEngine
from core.utils.time import utc_now
from core.verification.engine import VerificationEngine


class AppState:
    """Central application state with PostgreSQL/SQLite persistence."""

    def __init__(self):
        self.demo_mode: bool = settings.demo_mode
        self._db_initialized = False

        self.audit_logger = AuditLogger()
        self.policy_engine = PolicyEngine(default_deny=settings.effective_default_deny)
        self.risk_engine = RiskEngine()
        self.execution_engine = ExecutionEngine()
        self.verification_engine = VerificationEngine()
        self.lifecycle = ActionLifecycle(
            policy_engine=self.policy_engine,
            risk_engine=self.risk_engine,
            execution_engine=self.execution_engine,
            verification_engine=self.verification_engine,
            audit_logger=self.audit_logger,
            agent_resolver=lambda agent_id: self.get_agent(agent_id),
        )
        self.billing = BillingService()

        # In-memory cache for fast reads within a request (synced with DB)
        self._agents: dict[str, Agent] = {}
        self._policies: dict[str, Policy] = {}
        self._actions: dict[str, ActionRequest] = {}

        self._audit_persist: Callable[[AuditEvent], None] | None = None

    def init_database(self) -> None:
        if self._db_initialized:
            return
        init_engine(settings.database_url)
        self._ensure_schema()
        self._db_initialized = True
        self._wire_audit_persistence()

    def _ensure_schema(self) -> None:
        """Apply Alembic migrations to reach the latest schema."""
        from pathlib import Path

        from alembic import command
        from alembic.config import Config

        alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
        alembic_config = Config(str(alembic_ini))

        command.upgrade(alembic_config, "head")

    def _wire_audit_persistence(self) -> None:
        if self._audit_persist is not None:
            return
        def persist(event: AuditEvent) -> None:
            with session_scope() as session:
                AuditRepository(session).append(event)

        self._audit_persist = persist
        original_log = self.audit_logger.log

        def log_with_persist(*args, **kwargs):
            event = original_log(*args, **kwargs)
            if self._audit_persist:
                self._audit_persist(event)
            return event

        self.audit_logger.log = log_with_persist  # type: ignore[method-assign]

    def _with_session(self, fn):
        with session_scope() as session:
            return fn(session)

    def get_agent(self, agent_id: str) -> Agent | None:
        if agent_id in self._agents:
            return self._agents[agent_id]
        if self._db_initialized:
            agent = self._with_session(lambda s: AgentRepository(s).get(agent_id))
            if agent:
                self._agents[agent_id] = agent
            return agent
        return None

    def save_agent(self, agent: Agent) -> Agent:
        self._agents[agent.id] = agent
        if self._db_initialized:
            self._with_session(lambda s: AgentRepository(s).save(agent))
        return agent

    def reload_agent(self, agent_id: str) -> Agent | None:
        self._agents.pop(agent_id, None)
        return self.get_agent(agent_id)

    def save_policy(self, policy: Policy) -> Policy:
        self._policies[policy.id] = policy
        if self._db_initialized:
            self._with_session(lambda s: PolicyRepository(s).save(policy))
        self.policy_engine.set_policies(self.list_policies())
        return policy

    def save_policy_snapshot(self, snapshot: dict) -> dict:
        if self._db_initialized:
            self._with_session(lambda s: PolicyVersionRepository(s).save_snapshot(snapshot))
        return snapshot

    def list_policy_versions(self, policy_id: str, *, limit: int = 50) -> list[dict]:
        if self._db_initialized:
            return self._with_session(
                lambda s: PolicyVersionRepository(s).list_for_policy(policy_id, limit=limit)
            )
        return []

    def get_policy_version(self, version_id: str) -> dict | None:
        if self._db_initialized:
            return self._with_session(lambda s: PolicyVersionRepository(s).get(version_id))
        return None

    def get_policy(self, policy_id: str) -> Policy | None:
        if policy_id in self._policies:
            return self._policies[policy_id]
        if self._db_initialized:
            policy = self._with_session(lambda s: PolicyRepository(s).get(policy_id))
            if policy:
                self._policies[policy_id] = policy
            return policy
        return None

    def list_agents(self) -> list[Agent]:
        if self._db_initialized:
            agents = self._with_session(lambda s: AgentRepository(s).list_all())
            for a in agents:
                self._agents[a.id] = a
            return agents
        return list(self._agents.values())

    def list_policies(self) -> list[Policy]:
        if self._db_initialized:
            policies = self._with_session(lambda s: PolicyRepository(s).list_all())
            for p in policies:
                self._policies[p.id] = p
            return policies
        return list(self._policies.values())

    def get_action(self, action_id: str) -> ActionRequest | None:
        if action_id in self._actions:
            return self._actions[action_id]
        if self._db_initialized:
            action = self._with_session(lambda s: ActionRepository(s).get(action_id))
            if action:
                self._actions[action_id] = action
            return action
        return None

    def save_action(self, action: ActionRequest, *, approval_status: str | None = None,
                    approval_actor: str | None = None, approval_reason: str | None = None) -> None:
        self._actions[action.id] = action
        if self._db_initialized:
            decided_at = utc_now() if approval_status in ("approved", "rejected") else None
            self._with_session(lambda s: ActionRepository(s).save(
                action, approval_status=approval_status,
                approval_actor=approval_actor, approval_reason=approval_reason,
                approval_decided_at=decided_at,
            ))

    def list_actions(self, *, agent_id: str | None = None, status: str | None = None,
                     limit: int = 50) -> list[ActionRequest]:
        if self._db_initialized:
            actions = self._with_session(
                lambda s: ActionRepository(s).list_all(agent_id=agent_id, status=status, limit=limit)
            )
            for a in actions:
                self._actions[a.id] = a
            return actions
        actions = list(self._actions.values())
        if agent_id:
            actions = [a for a in actions if a.agent_id == agent_id]
        if status:
            actions = [a for a in actions if a.status.value == status]
        return sorted(actions, key=lambda a: a.created_at, reverse=True)[:limit]

    def load_demo_data(self) -> None:
        self.demo_mode = settings.demo_mode
        self.policy_engine.set_default_deny(settings.effective_default_deny)

        if self._db_initialized:
            with session_scope() as session:
                agent_repo = AgentRepository(session)
                policy_repo = PolicyRepository(session)
                for agent in DEMO_AGENTS:
                    existing = agent_repo.get(agent.id)
                    if existing:
                        self._agents[agent.id] = existing
                    else:
                        agent_repo.save(agent)
                        self._agents[agent.id] = agent
                for policy in DEMO_POLICIES:
                    existing = policy_repo.get(policy.id)
                    if existing:
                        self._policies[policy.id] = existing
                    else:
                        policy_repo.save(policy)
                        self._policies[policy.id] = policy
        else:
            for agent in DEMO_AGENTS:
                self._agents[agent.id] = agent
            for policy in DEMO_POLICIES:
                self._policies[policy.id] = policy

        self.policy_engine.set_policies(list(self._policies.values()) or DEMO_POLICIES)
        if self._db_initialized:
            self.billing.ensure_default_account()
        self._restore_pending_approvals()

    def _restore_pending_approvals(self) -> None:
        """Reload pending approvals from DB after restart."""
        if not self._db_initialized:
            return
        pending = self._with_session(lambda s: ActionRepository(s).list_pending_approvals())
        self.lifecycle.reset()
        for action in pending:
            self.lifecycle._pending_approvals[action.id] = action
            self._actions[action.id] = action

    def reset_for_tests(self) -> None:
        """Clear all state for test isolation."""
        self._agents.clear()
        self._policies.clear()
        self._actions.clear()
        self.audit_logger._events.clear()
        self.lifecycle.reset()
        self.execution_engine.reset_execution_count()
        if self._db_initialized:
            drop_all_tables()
            create_all_tables()

    def get_stats(self) -> dict:
        actions = self.list_actions(limit=10000)
        agents = self.list_agents()
        audit_count = (
            self._with_session(lambda s: AuditRepository(s).count())
            if self._db_initialized
            else self.audit_logger.count()
        )
        today = utc_now().date()
        actions_today = [a for a in actions if a.created_at.date() == today]
        return {
            "demo_mode": self.demo_mode,
            "default_deny": settings.effective_default_deny,
            "active_agents": sum(1 for a in agents if a.status.value == "active"),
            "total_agents": len(agents),
            "verified_actions": sum(1 for a in actions if a.status.value == "verified"),
            "blocked_actions": sum(1 for a in actions if a.status.value in ("blocked", "denied")),
            "allowed_actions": sum(1 for a in actions if a.status.value in ("verified", "executed")),
            "failed_actions": sum(
                1 for a in actions if a.status.value in ("failed", "verification_failed")
            ),
            "pending_approvals": len(self.lifecycle.get_pending_approvals()),
            "total_actions": len(actions),
            "actions_today": len(actions_today),
            "total_policies": len(self.list_policies()),
            "audit_events": audit_count,
            "avg_trust_score": round(
                sum(a.trust_score for a in agents) / max(len(agents), 1), 1
            ),
            "data_label": "DEMO DATA" if self.demo_mode else "APPLICATION STATE",
        }


state = AppState()
