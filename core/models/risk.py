"""Risk assessment domain model."""

from enum import Enum

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskAssessment(BaseModel):
    """Explainable risk evaluation result."""

    risk_score: float = Field(ge=0, le=100)
    risk_level: RiskLevel
    reasons: list[str] = Field(default_factory=list)
    recommended_decision: str = "allow"
    factors: dict[str, float] = Field(default_factory=dict)
