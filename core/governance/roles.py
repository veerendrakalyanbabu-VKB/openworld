"""Role administration business logic."""

from fastapi import HTTPException, status

from apps.api.auth.roles import Role, get_agent_roles
from core.models.agent import Agent
from core.models.audit import AuditEventType
from core.utils.time import utc_now

ASSIGNABLE_ROLES = {Role.OPERATOR, Role.POLICY_ADMIN, Role.SYSTEM_ADMIN}


def roles_from_metadata(agent: Agent) -> list[str]:
    raw = agent.metadata.get("roles", [])
    stored = [r for r in raw if r != Role.AGENT.value]
    return sorted(set(stored))


def count_system_admins(agents: list[Agent]) -> int:
    return sum(1 for a in agents if Role.SYSTEM_ADMIN in get_agent_roles(a))


def assign_role(
    *,
    target: Agent,
    role: Role,
    actor_id: str,
    all_agents: list[Agent],
    audit_logger,
    correlation_id: str = "",
) -> tuple[Agent, list[str], list[str]]:
    if role == Role.AGENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot assign baseline agent role")
    if role not in ASSIGNABLE_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

    old_roles = roles_from_metadata(target)
    if role.value in old_roles:
        return target, old_roles, old_roles

    new_metadata = dict(target.metadata)
    roles_list = list(new_metadata.get("roles", []))
    if role.value not in roles_list:
        roles_list.append(role.value)
    new_metadata["roles"] = roles_list
    target.metadata = new_metadata
    target.updated_at = utc_now()

    new_roles = roles_from_metadata(target)
    audit_logger.log(
        AuditEventType.ROLE_ASSIGNED,
        actor=actor_id,
        subject=target.id,
        action=f"assign:{role.value}",
        details={"old_roles": old_roles, "new_roles": new_roles, "role": role.value},
        correlation_id=correlation_id,
    )
    return target, old_roles, new_roles


def revoke_role(
    *,
    target: Agent,
    role: Role,
    actor_id: str,
    all_agents: list[Agent],
    audit_logger,
    correlation_id: str = "",
) -> tuple[Agent, list[str], list[str]]:
    if role == Role.AGENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot revoke baseline agent role")

    old_roles = roles_from_metadata(target)
    if role.value not in old_roles:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not assigned")

    if role == Role.SYSTEM_ADMIN and count_system_admins(all_agents) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot remove the final system administrator",
        )

    new_metadata = dict(target.metadata)
    roles_list = [r for r in new_metadata.get("roles", []) if r != role.value]
    new_metadata["roles"] = roles_list
    target.metadata = new_metadata
    target.updated_at = utc_now()

    new_roles = roles_from_metadata(target)
    audit_logger.log(
        AuditEventType.ROLE_REVOKED,
        actor=actor_id,
        subject=target.id,
        action=f"revoke:{role.value}",
        details={"old_roles": old_roles, "new_roles": new_roles, "role": role.value},
        correlation_id=correlation_id,
    )
    return target, old_roles, new_roles
