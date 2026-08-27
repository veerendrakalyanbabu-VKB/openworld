"""Role definitions and resolution from persisted agent records."""

from enum import Enum

from core.models.agent import Agent


class Role(str, Enum):
    VIEWER = "viewer"
    AGENT = "agent"
    OPERATOR = "operator"
    POLICY_ADMIN = "policy_admin"
    SYSTEM_ADMIN = "system_admin"


_ROLE_ALIASES = {"admin": "system_admin"}


def get_agent_roles(agent: Agent) -> set[Role]:
    """Resolve roles from persisted agent metadata (never from request body)."""
    raw = agent.metadata.get("roles", [])
    roles: set[Role] = {Role.VIEWER, Role.AGENT}
    for value in raw:
        try:
            mapped = _ROLE_ALIASES.get(str(value), value)
            roles.add(Role(mapped))
        except ValueError:
            continue
    if Role.SYSTEM_ADMIN in roles:
        roles.update({Role.OPERATOR, Role.POLICY_ADMIN, Role.AGENT, Role.VIEWER})
    if Role.POLICY_ADMIN in roles:
        roles.update({Role.AGENT, Role.VIEWER})
    if Role.OPERATOR in roles:
        roles.update({Role.AGENT, Role.VIEWER})
    return roles


def has_any_role(roles: set[Role], *required: Role) -> bool:
    if Role.SYSTEM_ADMIN in roles:
        return True
    return any(role in roles for role in required)
