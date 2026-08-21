"""Audit domain model."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from core.utils.time import utc_now


class AuditEventType(str, Enum):
    AGENT_REGISTERED = "agent_registered"
    ACTION_REQUESTED = "action_requested"
    POLICY_EVALUATED = "policy_evaluated"
    RISK_ASSESSED = "risk_assessed"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    ACTION_EXECUTED = "action_executed"
    ACTION_BLOCKED = "action_blocked"
    VERIFICATION_COMPLETED = "verification_completed"
    POLICY_CREATED = "policy_created"
    POLICY_UPDATED = "policy_updated"
    POLICY_DISABLED = "policy_disabled"
    POLICY_ENABLED = "policy_enabled"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"
    AUDIT_EXPORTED = "audit_exported"
    TRUST_UPDATED = "trust_updated"


class AuditEvent(BaseModel):
    """Immutable audit record."""

    id: str
    event_type: AuditEventType
    actor: str
    subject: str
    action: str = ""
    decision: str = ""
    policy_id: str | None = None
    risk_level: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str = ""
    timestamp: datetime = Field(default_factory=utc_now)
    evidence: list[str] = Field(default_factory=list)
