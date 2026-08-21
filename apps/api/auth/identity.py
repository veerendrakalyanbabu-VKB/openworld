"""Identity provider abstraction for future external IdP integration."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from apps.api.auth.jwt import decode_agent_token


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """Resolved identity after authentication (before authorization)."""

    agent_id: str


class IdentityProvider(ABC):
    @abstractmethod
    def authenticate_bearer(self, token: str) -> AuthenticatedPrincipal:
        """Validate bearer token and return principal identity."""


class JwtIdentityProvider(IdentityProvider):
    """Current production path: HS256 JWT with agent ID in ``sub`` claim."""

    def authenticate_bearer(self, token: str) -> AuthenticatedPrincipal:
        agent_id = decode_agent_token(token)
        return AuthenticatedPrincipal(agent_id=agent_id)


_default_provider = JwtIdentityProvider()


def get_identity_provider() -> IdentityProvider:
    return _default_provider
