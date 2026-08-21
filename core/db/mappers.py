"""Map between ORM rows and Pydantic domain models."""

from core.db.models import ActionRow, AgentRow, AuditEventRow, PolicyRow
from core.models.action import ActionRequest, ActionStageRecord, ActionStatus, PolicyDecision
from core.models.agent import Agent, AgentStatus, TrustDimensions
from core.models.audit import AuditEvent, AuditEventType
from core.models.policy import Policy, PolicyCondition, PolicyEffect, PolicyRule


def agent_to_domain(row: AgentRow) -> Agent:
    td = row.trust_dimensions or {}
    return Agent(
        id=row.id,
        name=row.name,
        description=row.description or "",
        owner=row.owner or "system",
        status=AgentStatus(row.status),
        capabilities=row.capabilities or [],
        trust_dimensions=TrustDimensions(**td) if td else TrustDimensions(
            identity=100, policy=100, reliability=100, verification=100, violations=100
        ),
        metadata=row.metadata_ or {},
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def agent_from_domain(agent: Agent) -> AgentRow:
    return AgentRow(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        owner=agent.owner,
        status=agent.status.value,
        capabilities=agent.capabilities,
        trust_dimensions=agent.trust_dimensions.model_dump(),
        metadata_=agent.metadata,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


def policy_to_domain(row: PolicyRow) -> Policy:
    rules = []
    for r in row.rules or []:
        conditions = [
            PolicyCondition(**c) if isinstance(c, dict) else c for c in r.get("conditions", [])
        ]
        rules.append(
            PolicyRule(
                id=r["id"],
                name=r.get("name", ""),
                agent_match=r.get("agent_match"),
                action_match=r.get("action_match"),
                capability_match=r.get("capability_match"),
                conditions=conditions,
                effect=PolicyEffect(r["effect"]),
                priority=r.get("priority", 100),
                description=r.get("description", ""),
            )
        )
    return Policy(
        id=row.id,
        name=row.name,
        description=row.description or "",
        version=row.version or "1.0",
        rules=rules,
        enabled=row.enabled,
    )


def policy_from_domain(policy: Policy) -> PolicyRow:
    return PolicyRow(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        version=policy.version,
        rules=[r.model_dump() for r in policy.rules],
        enabled=policy.enabled,
    )


def action_to_domain(row: ActionRow) -> ActionRequest:
    stages = [ActionStageRecord(**s) if isinstance(s, dict) else s for s in (row.stages or [])]
    policy_decision = None
    if row.policy_decision:
        policy_decision = PolicyDecision(**row.policy_decision)
    return ActionRequest(
        id=row.id,
        agent_id=row.agent_id,
        agent_name=row.agent_name or "",
        action=row.action,
        target=row.target or "",
        parameters=row.parameters or {},
        context=row.context or {},
        requested_permissions=row.requested_permissions or [],
        status=ActionStatus(row.status),
        policy_decision=policy_decision,
        stages=stages,
        correlation_id=row.correlation_id or "",
        execution_result=row.execution_result,
        verification_id=row.verification_id,
        risk_score=row.risk_score,
        risk_level=row.risk_level,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def action_from_domain(action: ActionRequest, approval_status: str | None = None,
                       approval_actor: str | None = None, approval_reason: str | None = None,
                       approval_decided_at=None) -> ActionRow:
    return ActionRow(
        id=action.id,
        agent_id=action.agent_id,
        agent_name=action.agent_name,
        action=action.action,
        target=action.target,
        parameters=action.parameters,
        context=action.context,
        requested_permissions=action.requested_permissions,
        status=action.status.value,
        policy_decision=action.policy_decision.model_dump(mode="json") if action.policy_decision else None,
        stages=[s.model_dump(mode="json") for s in action.stages],
        correlation_id=action.correlation_id,
        execution_result=action.execution_result,
        verification_id=action.verification_id,
        risk_score=action.risk_score,
        risk_level=action.risk_level,
        approval_status=approval_status,
        approval_actor=approval_actor,
        approval_reason=approval_reason,
        approval_decided_at=approval_decided_at,
        created_at=action.created_at,
        updated_at=action.updated_at,
    )


def audit_to_domain(row: AuditEventRow) -> AuditEvent:
    return AuditEvent(
        id=row.id,
        event_type=AuditEventType(row.event_type),
        actor=row.actor,
        subject=row.subject,
        action=row.action or "",
        decision=row.decision or "",
        policy_id=row.policy_id,
        risk_level=row.risk_level,
        details=row.details or {},
        correlation_id=row.correlation_id or "",
        evidence=row.evidence or [],
        timestamp=row.timestamp,
    )


def audit_from_domain(event: AuditEvent) -> AuditEventRow:
    return AuditEventRow(
        id=event.id,
        event_type=event.event_type.value,
        actor=event.actor,
        subject=event.subject,
        action=event.action,
        decision=event.decision,
        policy_id=event.policy_id,
        risk_level=event.risk_level,
        details=event.details,
        correlation_id=event.correlation_id,
        evidence=event.evidence,
        timestamp=event.timestamp,
    )
