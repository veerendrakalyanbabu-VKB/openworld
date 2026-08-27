"""Action request domain model."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from core.utils.time import utc_now


class ActionStatus(str, Enum):
    REQUESTED = "requested"
    IDENTITY_VERIFIED = "identity_verified"
    POLICY_EVALUATED = "policy_evaluated"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    DENIED = "denied"
    EXECUTING = "executing"
    EXECUTED = "executed"
    VERIFIED = "verified"
    VERIFICATION_FAILED = "verification_failed"
    FAILED = "failed"
    BLOCKED = "blocked"


class ActionStage(str, Enum):
    REQUESTED = "requested"
    IDENTITY = "identity"
    CAPABILITY = "capability"
    POLICY = "policy"
    RISK = "risk"
    DECISION = "decision"
    APPROVAL = "approval"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    AUDIT = "audit"
    COMPLETE = "complete"


class PolicyDecisionType(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class PolicyDecision(BaseModel):
    """Result of policy evaluation."""

    decision: PolicyDecisionType
    policy_id: str | None = None
    policy_name: str | None = None
    rule_id: str | None = None
    reasons: list[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=utc_now)


class ActionStageRecord(BaseModel):
    """Record of a stage in the action lifecycle."""

    stage: ActionStage
    status: str
    timestamp: datetime = Field(default_factory=utc_now)
    details: dict = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)


class ActionRequest(BaseModel):
    """An action requested by an agent."""

    id: str
    agent_id: str
    agent_name: str = ""
    action: str
    target: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    requested_permissions: list[str] = Field(default_factory=list)
    status: ActionStatus = ActionStatus.REQUESTED
    policy_decision: PolicyDecision | None = None
    stages: list[ActionStageRecord] = Field(default_factory=list)
    correlation_id: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    execution_result: dict | None = None
    verification_id: str | None = None
    risk_score: float | None = None
    risk_level: str | None = None
