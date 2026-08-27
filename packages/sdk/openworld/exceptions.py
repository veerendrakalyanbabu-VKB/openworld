"""OpenWorld SDK exception hierarchy."""

from typing import Any


class OpenWorldError(Exception):
    """Base exception for OpenWorld SDK errors."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        request_id: str | None = None,
        detail: Any = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.request_id = request_id
        self.detail = detail


class AuthError(OpenWorldError):
    """Authentication failed (401)."""


class ForbiddenError(OpenWorldError):
    """Authorization failed (403)."""


class NotFoundError(OpenWorldError):
    """Resource not found (404)."""


class ConflictError(OpenWorldError):
    """Conflict with current state (409)."""


class TimeoutError(OpenWorldError):
    """Request timed out."""
