"""API gateway boundary — cross-cutting concerns without Trust Core logic."""

from apps.api.gateway.errors import get_request_id, register_exception_handlers
from apps.api.gateway.middleware import GatewayMiddleware
from apps.api.gateway.rate_limit import NoOpRateLimiter, RateLimiter, RateLimitResult

__all__ = [
    "GatewayMiddleware",
    "NoOpRateLimiter",
    "RateLimitResult",
    "RateLimiter",
    "get_request_id",
    "register_exception_handlers",
]
