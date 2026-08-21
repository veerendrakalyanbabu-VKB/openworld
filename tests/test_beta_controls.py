"""In-process rate limiter and tenant labeling tests."""

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from apps.api.gateway.errors import register_exception_handlers
from apps.api.gateway.middleware import GatewayMiddleware
from apps.api.gateway.rate_limit import MemoryRateLimiter
from apps.api.tenancy import DEFAULT_TENANT_ID, parse_tenant_id


def test_memory_limiter_blocks_after_limit():
    limiter = MemoryRateLimiter(2, window_seconds=60)

    async def _hit():
        scope = {"type": "http", "path": "/api/v1/stats", "headers": []}
        request = Request(scope)
        return await limiter.check(request, client_key="k1")

    async def run():
        r1 = await _hit()
        r2 = await _hit()
        r3 = await _hit()
        assert r1.allowed and r2.allowed
        assert r3.allowed is False
        assert r3.remaining == 0

    asyncio.run(run())


def test_memory_limiter_exempts_health():
    limiter = MemoryRateLimiter(1, window_seconds=60)

    async def run():
        scope = {"type": "http", "path": "/api/v1/health", "headers": []}
        request = Request(scope)
        first = await limiter.check(request, client_key="k")
        second = await limiter.check(request, client_key="k")
        assert first.allowed and second.allowed

    asyncio.run(run())


def test_tenant_header_is_label_only():
    scope = {
        "type": "http",
        "path": "/",
        "headers": [(b"x-openworld-tenant", b"beta-lab")],
    }
    request = Request(scope)
    assert parse_tenant_id(request) == "beta-lab"
    bad = Request({"type": "http", "path": "/", "headers": [(b"x-openworld-tenant", b"../etc")]})
    assert parse_tenant_id(bad) == DEFAULT_TENANT_ID


def test_gateway_returns_429_when_limited():
    app = FastAPI()
    app.add_middleware(GatewayMiddleware, rate_limiter=MemoryRateLimiter(1, window_seconds=60))
    register_exception_handlers(app)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 429
