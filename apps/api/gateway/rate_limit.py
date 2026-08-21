"""Rate limiting abstraction — hook interface plus an in-process limiter."""

from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass
from time import monotonic

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


class MemoryRateLimiter(RateLimiter):
    """Fixed-window limiter for a single API process. Not a distributed quota."""

    def __init__(self, limit_per_minute: int, *, window_seconds: float = 60.0):
        self.limit_per_minute = max(0, limit_per_minute)
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def check(self, request: Request, *, client_key: str) -> RateLimitResult:
        path = request.url.path
        if path.endswith("/health") or path.endswith("/ready"):
            return RateLimitResult(allowed=True, limit=self.limit_per_minute)
        if self.limit_per_minute <= 0:
            return RateLimitResult(allowed=True)
        now = monotonic()
        bucket = self._hits[client_key]
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.limit_per_minute:
            retry = self.window_seconds - (now - bucket[0])
            return RateLimitResult(
                allowed=False,
                retry_after_seconds=max(retry, 1.0),
                limit=self.limit_per_minute,
                remaining=0,
            )
        bucket.append(now)
        return RateLimitResult(
            allowed=True,
            limit=self.limit_per_minute,
            remaining=self.limit_per_minute - len(bucket),
        )
