"""JWT token creation and validation."""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status

from apps.api.config import settings


class TokenError(Exception):
    pass


def create_agent_token(agent_id: str, *, expires_minutes: int | None = None) -> str:
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=expires_minutes or settings.jwt_expire_minutes)
    payload = {
        "sub": agent_id,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": exp,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_agent_token(token: str) -> str:
    """Validate JWT and return agent_id (sub claim)."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["sub", "exp", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from None
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from None

    agent_id = payload.get("sub")
    if not agent_id or not isinstance(agent_id, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    return agent_id
