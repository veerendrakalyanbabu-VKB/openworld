"""Capability and permission validation for agent actions."""

import fnmatch

from pydantic import BaseModel, Field

from core.models.agent import Agent


class PermissionResult(BaseModel):
    """Result of capability/permission validation."""

    permitted: bool
    missing_capabilities: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class PermissionValidator:
    """Validates that an agent possesses required capabilities."""

    def validate(
        self,
        agent: Agent,
        action: str,
        requested_permissions: list[str] | None = None,
    ) -> PermissionResult:
        required = requested_permissions or [action]
        missing: list[str] = []

        for perm in required:
            if not self._has_capability(agent, perm) and not self._has_capability(agent, action):
                if perm not in missing:
                    missing.append(perm)

        if missing:
            return PermissionResult(
                permitted=False,
                missing_capabilities=missing,
                reasons=[
                    f"Agent '{agent.name}' lacks capability: {cap}"
                    for cap in missing
                ],
            )

        return PermissionResult(
            permitted=True,
            reasons=[f"Agent '{agent.name}' has required capability for '{action}'"],
        )

    def _has_capability(self, agent: Agent, capability: str) -> bool:
        for cap in agent.capabilities:
            if cap == capability:
                return True
            if fnmatch.fnmatch(capability, cap):
                return True
            if fnmatch.fnmatch(cap, capability):
                return True
            cap_base = cap.rsplit(".", 1)[0] if "." in cap else cap
            req_base = capability.rsplit(".", 1)[0] if "." in capability else capability
            if cap_base == req_base and cap.endswith(".*"):
                return True
        return False
