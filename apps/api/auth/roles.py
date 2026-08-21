"""Role definitions and resolution from persisted agent records."""

from enum import Enum

from core.models.agent import Agent


class Role(str, Enum):
    AGENT = "agent"
    OPERATOR = "operator"
    POLICY_ADMIN = "policy_admin"
    SYSTEM_ADMIN = "system_admin"


def get_agent_roles(agent: Agent) -> set[Role]:
    """Resolve roles from persisted agent metadata (never from request body)."""
    raw = agent.metadata.get("roles", [])
    roles: set[Role] = {Role.AGENT}
    for value in raw:
        try:
            roles.add(Role(value))
        except ValueError:
            continue
    if Role.SYSTEM_ADMIN in roles:
        roles.update({Role.OPERATOR, Role.POLICY_ADMIN, Role.AGENT})
    if Role.POLICY_ADMIN in roles:
        roles.add(Role.AGENT)
    if Role.OPERATOR in roles:
        roles.add(Role.AGENT)
    return roles


def has_any_role(roles: set[Role], *required: Role) -> bool:
    if Role.SYSTEM_ADMIN in roles:
        return True
    return any(role in roles for role in required)
