"""Capability domain model."""

from pydantic import BaseModel, Field


class Capability(BaseModel):
    """A discrete capability an agent can possess."""

    id: str
    name: str
    description: str = ""
    category: str = "general"
    sensitivity: str = "low"  # low, medium, high, critical
    metadata: dict = Field(default_factory=dict)
