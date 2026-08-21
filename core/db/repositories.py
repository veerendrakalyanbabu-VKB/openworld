"""Repository layer — persistence without business logic."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.db.mappers import (
    action_from_domain,
    action_to_domain,
    agent_from_domain,
    agent_to_domain,
    audit_from_domain,
    audit_to_domain,
    policy_from_domain,
    policy_to_domain,
)
from core.db.models import ActionRow, AgentRow, AuditEventRow, IdempotencyRow, PolicyRow, PolicyVersionRow
from core.models.action import ActionRequest, ActionStatus
from core.models.agent import Agent
from core.models.audit import AuditEvent
from core.models.policy import Policy
from core.utils.time import utc_now


class AgentRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, agent_id: str) -> Agent | None:
        row = self.session.get(AgentRow, agent_id)
        return agent_to_domain(row) if row else None

    def list_all(self) -> list[Agent]:
        rows = self.session.scalars(select(AgentRow)).all()
        return [agent_to_domain(r) for r in rows]

    def save(self, agent: Agent) -> Agent:
        row = self.session.get(AgentRow, agent.id)
        if row:
            row.name = agent.name
            row.description = agent.description
            row.owner = agent.owner
            row.status = agent.status.value
            row.capabilities = agent.capabilities
            row.trust_dimensions = agent.trust_dimensions.model_dump()
            metadata = {**(agent.metadata or {}), "organization": agent.organization}
            row.metadata_ = metadata
            row.updated_at = utc_now()
        else:
            self.session.add(agent_from_domain(agent))
        self.session.flush()
        return agent

    def upsert_many(self, agents: list[Agent]) -> None:
        for agent in agents:
            self.save(agent)


class PolicyRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, policy_id: str) -> Policy | None:
        row = self.session.get(PolicyRow, policy_id)
        return policy_to_domain(row) if row else None

    def list_all(self) -> list[Policy]:
        rows = self.session.scalars(select(PolicyRow)).all()
        return [policy_to_domain(r) for r in rows]

    def save(self, policy: Policy) -> Policy:
        row = self.session.get(PolicyRow, policy.id)
        if row:
            row.name = policy.name
            row.description = policy.description
            row.version = policy.version
            row.rules = [r.model_dump() for r in policy.rules]
            row.enabled = policy.enabled
            row.updated_at = utc_now()
        else:
            self.session.add(policy_from_domain(policy))
        self.session.flush()
        return policy

    def upsert_many(self, policies: list[Policy]) -> None:
        for policy in policies:
            self.save(policy)


class ActionRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, action_id: str) -> ActionRequest | None:
        row = self.session.get(ActionRow, action_id)
        return action_to_domain(row) if row else None

    def save(self, action: ActionRequest, *, approval_status: str | None = None,
             approval_actor: str | None = None, approval_reason: str | None = None,
             approval_decided_at: datetime | None = None) -> ActionRequest:
        row = self.session.get(ActionRow, action.id)
        if row:
            row.status = action.status.value
            row.policy_decision = action.policy_decision.model_dump(mode="json") if action.policy_decision else None
            row.stages = [s.model_dump(mode="json") for s in action.stages]
            row.execution_result = action.execution_result
            row.verification_id = action.verification_id
            row.risk_score = action.risk_score
            row.risk_level = action.risk_level
            row.updated_at = utc_now()
            if approval_status is not None:
                row.approval_status = approval_status
            if approval_actor is not None:
                row.approval_actor = approval_actor
            if approval_reason is not None:
                row.approval_reason = approval_reason
            if approval_decided_at is not None:
                row.approval_decided_at = approval_decided_at
        else:
            self.session.add(action_from_domain(
                action, approval_status=approval_status,
                approval_actor=approval_actor, approval_reason=approval_reason,
                approval_decided_at=approval_decided_at,
            ))
        self.session.flush()
        return action

    def list_all(self, *, agent_id: str | None = None, status: str | None = None,
                 limit: int = 50) -> list[ActionRequest]:
        stmt = select(ActionRow)
        if agent_id:
            stmt = stmt.where(ActionRow.agent_id == agent_id)
        if status:
            stmt = stmt.where(ActionRow.status == status)
        stmt = stmt.order_by(ActionRow.created_at.desc()).limit(limit)
        rows = self.session.scalars(stmt).all()
        return [action_to_domain(r) for r in rows]

    def list_pending_approvals(self) -> list[ActionRequest]:
        stmt = select(ActionRow).where(ActionRow.status == ActionStatus.PENDING_APPROVAL.value)
        rows = self.session.scalars(stmt).all()
        return [action_to_domain(r) for r in rows]


class AuditRepository:
    def __init__(self, session: Session):
        self.session = session

    def append(self, event: AuditEvent) -> AuditEvent:
        self.session.add(audit_from_domain(event))
        self.session.flush()
        return event

    def count(self) -> int:
        return len(self.session.scalars(select(AuditEventRow)).all())

    def get_events(self, *, limit: int = 100, offset: int = 0, agent: str | None = None,
                   event_type: str | None = None, decision: str | None = None,
                   risk_level: str | None = None, subject: str | None = None,
                   correlation_id: str | None = None) -> list[AuditEvent]:
        stmt = select(AuditEventRow)
        if agent:
            stmt = stmt.where(
                AuditEventRow.actor.ilike(f"%{agent}%") | AuditEventRow.subject.ilike(f"%{agent}%")
            )
        if event_type:
            stmt = stmt.where(AuditEventRow.event_type == event_type)
        if decision:
            stmt = stmt.where(AuditEventRow.decision == decision)
        if risk_level:
            stmt = stmt.where(AuditEventRow.risk_level == risk_level)
        if subject:
            stmt = stmt.where(AuditEventRow.subject == subject)
        if correlation_id:
            stmt = stmt.where(AuditEventRow.correlation_id == correlation_id)
        stmt = stmt.order_by(AuditEventRow.timestamp.desc()).offset(offset).limit(limit)
        rows = self.session.scalars(stmt).all()
        return [audit_to_domain(r) for r in rows]


class PolicyVersionRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_snapshot(self, snapshot: dict) -> dict:
        row = PolicyVersionRow(
            id=snapshot["id"],
            policy_id=snapshot["policy_id"],
            version=snapshot["version"],
            name=snapshot["name"],
            description=snapshot.get("description", ""),
            rules=snapshot.get("rules", []),
            enabled=snapshot.get("enabled", True),
            change_action=snapshot["change_action"],
            created_by=snapshot["created_by"],
            created_at=snapshot.get("created_at", utc_now()),
        )
        self.session.add(row)
        self.session.flush()
        return snapshot

    def list_for_policy(self, policy_id: str, *, limit: int = 50) -> list[dict]:
        stmt = (
            select(PolicyVersionRow)
            .where(PolicyVersionRow.policy_id == policy_id)
            .order_by(PolicyVersionRow.created_at.desc())
            .limit(limit)
        )
        rows = self.session.scalars(stmt).all()
        return [
            {
                "id": r.id,
                "policy_id": r.policy_id,
                "version": r.version,
                "name": r.name,
                "description": r.description,
                "rules": r.rules,
                "enabled": r.enabled,
                "change_action": r.change_action,
                "created_by": r.created_by,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    def get(self, version_id: str) -> dict | None:
        row = self.session.get(PolicyVersionRow, version_id)
        if not row:
            return None
        return {
            "id": row.id,
            "policy_id": row.policy_id,
            "version": row.version,
            "name": row.name,
            "description": row.description,
            "rules": row.rules,
            "enabled": row.enabled,
            "change_action": row.change_action,
            "created_by": row.created_by,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }


class IdempotencyRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, agent_id: str, idempotency_key: str) -> IdempotencyRow | None:
        stmt = select(IdempotencyRow).where(
            IdempotencyRow.agent_id == agent_id,
            IdempotencyRow.idempotency_key == idempotency_key,
        )
        return self.session.scalars(stmt).first()

    def save(self, record: IdempotencyRow) -> IdempotencyRow:
        self.session.add(record)
        self.session.flush()
        return record
