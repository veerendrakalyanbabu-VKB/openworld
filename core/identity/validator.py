"""Identity validation for agent actions."""

from pydantic import BaseModel, Field

from core.models.agent import Agent, AgentStatus


class IdentityResult(BaseModel):
    """Result of identity validation."""

    valid: bool
    reasons: list[str] = Field(default_factory=list)


class IdentityValidator:
    """Validates agent identity before action processing."""

    def validate(self, agent: Agent) -> IdentityResult:
        if agent.status == AgentStatus.SUSPENDED:
            return IdentityResult(
                valid=False,
                reasons=[f"Agent '{agent.name}' is suspended"],
            )
        if agent.status == AgentStatus.INACTIVE:
            return IdentityResult(
                valid=False,
                reasons=[f"Agent '{agent.name}' is inactive"],
            )
        if agent.status == AgentStatus.PENDING:
            return IdentityResult(
                valid=False,
                reasons=[f"Agent '{agent.name}' is pending activation"],
            )
        if agent.status != AgentStatus.ACTIVE:
            return IdentityResult(
                valid=False,
                reasons=[f"Agent '{agent.name}' has invalid status: {agent.status.value}"],
            )
        return IdentityResult(
            valid=True,
            reasons=[f"Agent '{agent.name}' identity confirmed (status: active)"],
        )
