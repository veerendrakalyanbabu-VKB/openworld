"""Permission domain model."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from core.utils.time import utc_now


class PermissionScope(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class Permission(BaseModel):
    """Permission granted to an agent."""

    id: str
    agent_id: str
    capability: str
    scope: PermissionScope = PermissionScope.EXECUTE
    granted_by: str = "system"
    granted_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime | None = None
    constraints: dict = Field(default_factory=dict)
    active: bool = True
