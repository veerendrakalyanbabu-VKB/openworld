"""Policy domain model."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from core.utils.time import utc_now


class PolicyEffect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class ConditionOperator(str, Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    CONTAINS = "contains"
    MATCHES = "matches"


class PolicyCondition(BaseModel):
    """A single condition in a policy rule."""

    field: str
    operator: ConditionOperator
    value: Any


class PolicyRule(BaseModel):
    """A single rule within a policy."""

    id: str
    name: str = ""
    agent_match: str | None = None  # agent name or * for any
    action_match: str | None = None  # action pattern
    capability_match: str | None = None
    conditions: list[PolicyCondition] = Field(default_factory=list)
    effect: PolicyEffect = PolicyEffect.ALLOW
    priority: int = 100
    description: str = ""


class Policy(BaseModel):
    """A policy governing agent actions."""

    id: str
    name: str
    description: str = ""
    version: str = "1.0"
    rules: list[PolicyRule] = Field(default_factory=list)
    enabled: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict = Field(default_factory=dict)
