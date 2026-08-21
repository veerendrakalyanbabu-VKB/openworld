"""Typed request/response models for the OpenWorld SDK."""

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    demo_mode: bool = False


class ReadinessResponse(BaseModel):
    status: str
    service: str
    database: str
    demo_mode: bool = False


class StatsResponse(BaseModel):
    active_agents: int
    verified_actions: int
    blocked_actions: int
    pending_approvals: int
    avg_trust_score: float
    demo_mode: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    agent_id: str
    expires_in_minutes: int
    label: str = ""


class DemoAgentToken(BaseModel):
    agent_id: str
    agent_name: str
    access_token: str
    roles: list[str] = Field(default_factory=list)


class DemoAgentsResponse(BaseModel):
    label: str
    agents: list[DemoAgentToken]


class AgentSummary(BaseModel):
    id: str
    name: str
    status: str
    capabilities: list[str] = Field(default_factory=list)
    trust_dimensions: dict[str, Any] = Field(default_factory=dict)


class AgentListResponse(BaseModel):
    agents: list[AgentSummary]
    total: int
    demo_mode: bool = False


class AgentDetailResponse(BaseModel):
    agent: dict[str, Any]
    recent_actions: list[dict[str, Any]] = Field(default_factory=list)
    demo_mode: bool = False


class ActionSubmitRequest(BaseModel):
    action: str
    target: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    requested_permissions: list[str] = Field(default_factory=list)
    auto_approve: bool = False


class ActionResponse(BaseModel):
    action: dict[str, Any]
    demo_mode: bool = False


class ActionListResponse(BaseModel):
    actions: list[dict[str, Any]]
    total: int
    demo_mode: bool = False


class SimulateRequest(BaseModel):
    action: str
    target: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


class SimulateResponse(BaseModel):
    simulation: bool = True
    label: str = ""
    identity: dict[str, Any] = Field(default_factory=dict)
    capability: dict[str, Any] = Field(default_factory=dict)
    policy: dict[str, Any] = Field(default_factory=dict)
    risk: dict[str, Any] = Field(default_factory=dict)
    predicted_outcome: str = ""
    agent: str = ""
    action: str = ""


class ApprovalListResponse(BaseModel):
    approvals: list[dict[str, Any]]
    total: int
    demo_mode: bool = False
    actor: str = ""


class ApprovalResponse(BaseModel):
    approval: dict[str, Any]
    demo_mode: bool = False
    actor: str = ""


class PolicyListResponse(BaseModel):
    policies: list[dict[str, Any]]
    total: int
    demo_mode: bool = False


class PolicyResponse(BaseModel):
    policy: dict[str, Any]
    demo_mode: bool = False


class AuditListResponse(BaseModel):
    events: list[dict[str, Any]]
    total: int
    demo_mode: bool = False
    label: str | None = None
    scoped_to: str | None = None


class RoleListResponse(BaseModel):
    agent_id: str
    roles: list[str]
    stored_roles: list[str] = Field(default_factory=list)
    demo_mode: bool = False


class RoleMutationResponse(BaseModel):
    agent_id: str
    old_roles: list[str]
    new_roles: list[str]
    demo_mode: bool = False
