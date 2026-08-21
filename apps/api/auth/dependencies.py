"""FastAPI authentication dependencies."""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from apps.api.auth.identity import get_identity_provider
from apps.api.auth.roles import Role, get_agent_roles, has_any_role
from apps.api.config import settings
from apps.api.state import state
from core.models.agent import Agent

_bearer = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedActor:
    agent: Agent
    roles: set[Role]


async def get_current_agent(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Agent:
    return (await get_authenticated_actor(credentials)).agent


async def get_authenticated_actor(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedActor:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    principal = get_identity_provider().authenticate_bearer(credentials.credentials)
    agent = state.get_agent(principal.agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Agent not found")
    return AuthenticatedActor(agent=agent, roles=get_agent_roles(agent))


async def get_optional_authenticated_actor(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedActor | None:
    if credentials is None:
        return None
    if credentials.scheme.lower() != "bearer":
        return None
    return await get_authenticated_actor(credentials)


def require_roles(*required: Role):
    async def _dependency(
        actor: AuthenticatedActor = Depends(get_authenticated_actor),
    ) -> AuthenticatedActor:
        if not has_any_role(actor.roles, *required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient authorization",
            )
        return actor

    return _dependency


require_operator = require_roles(Role.OPERATOR, Role.SYSTEM_ADMIN)
require_policy_admin = require_roles(Role.POLICY_ADMIN, Role.SYSTEM_ADMIN)
require_system_admin = require_roles(Role.SYSTEM_ADMIN)


async def get_optional_agent(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Agent | None:
    actor = await get_optional_authenticated_actor(credentials)
    return actor.agent if actor else None


def require_demo_mode() -> None:
    if not settings.demo_mode:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Demo-only endpoint")
