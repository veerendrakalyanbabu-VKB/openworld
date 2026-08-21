"""Rate limiting abstraction — hook interface without Redis implementation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from fastapi import Request


@dataclass
class RateLimitResult:
    allowed: bool
    retry_after_seconds: float | None = None
    limit: int | None = None
    remaining: int | None = None


class RateLimiter(ABC):
    """Abstract rate limiter — swap in Redis/token-bucket implementations later."""

    @abstractmethod
    async def check(self, request: Request, *, client_key: str) -> RateLimitResult:
        """Return whether the request is within rate limits."""


class NoOpRateLimiter(RateLimiter):
    """Default pass-through rate limiter (no enforcement)."""

    async def check(self, request: Request, *, client_key: str) -> RateLimitResult:
        return RateLimitResult(allowed=True)
