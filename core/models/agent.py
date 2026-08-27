"""Agent domain model."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from core.utils.time import utc_now


class AgentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class TrustDimensions(BaseModel):
    identity: float = 100.0
    policy: float = 100.0
    reliability: float = 100.0
    verification: float = 100.0
    violations: float = 100.0

    @property
    def overall(self) -> float:
        return round(
            self.identity * 0.25
            + self.policy * 0.25
            + self.reliability * 0.2
            + self.verification * 0.2
            + self.violations * 0.1,
            1,
        )


class Agent(BaseModel):
    """An AI agent registered in OpenWorld."""

    id: str
    name: str
    description: str = ""
    owner: str = "system"
    organization: str = "default"
    status: AgentStatus = AgentStatus.ACTIVE
    capabilities: list[str] = Field(default_factory=list)
    trust_dimensions: TrustDimensions = Field(default_factory=TrustDimensions)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @property
    def trust_score(self) -> float:
        return self.trust_dimensions.overall
