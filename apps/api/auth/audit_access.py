"""Shared audit read/export authorization scoping."""

from fastapi import HTTPException, status

from apps.api.auth.dependencies import AuthenticatedActor
from apps.api.auth.roles import Role, has_any_role
from apps.api.config import settings


def audit_scope_agent_id(actor: AuthenticatedActor) -> str | None:
    """Production agents may only read audit for their own subject."""
    if settings.demo_mode:
        return None
    if has_any_role(actor.roles, Role.OPERATOR, Role.POLICY_ADMIN, Role.SYSTEM_ADMIN):
        return None
    return actor.agent.id


def resolve_audit_subject(actor: AuthenticatedActor, subject: str | None) -> str | None:
    scope_agent = audit_scope_agent_id(actor)
    if scope_agent and subject and subject != scope_agent:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot read audit for other subjects")
    if scope_agent and not subject:
        return scope_agent
    return subject


def can_access_intelligence(actor: AuthenticatedActor | None) -> bool:
    if settings.demo_mode and actor is None:
        return True
    return actor is not None


def intelligence_access_level(actor: AuthenticatedActor | None) -> str:
    if actor is None:
        return "public"
    if has_any_role(actor.roles, Role.SYSTEM_ADMIN, Role.POLICY_ADMIN):
        return "admin"
    if has_any_role(actor.roles, Role.OPERATOR):
        return "operator"
    return "agent"
