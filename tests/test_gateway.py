"""Gateway boundary tests — correlation, bounds, rate-limit hook, structured errors."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.gateway.errors import register_exception_handlers, structured_error
from apps.api.gateway.middleware import GatewayMiddleware
from apps.api.gateway.rate_limit import RateLimiter, RateLimitResult
from apps.api.main import app as openworld_app
from tests.conftest import action_headers


class _DenyLimiter(RateLimiter):
    async def check(self, request, *, client_key: str) -> RateLimitResult:
        return RateLimitResult(allowed=False, retry_after_seconds=9, limit=1, remaining=0)


def _gateway_app(**middleware_kwargs) -> FastAPI:
    app = FastAPI()
    app.add_middleware(GatewayMiddleware, **middleware_kwargs)
    register_exception_handlers(app)

    @app.get("/ok")
    def ok():
        return {"status": "ok"}

    @app.post("/echo")
    def echo():
        return {"ok": True}

    @app.get("/big")
    def big():
        return {"data": "x" * 400}

    return app


def test_echoes_client_correlation_id():
    client = TestClient(openworld_app)
    response = client.get("/api/v1/health", headers={"X-Request-ID": "trace-fixed-id"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "trace-fixed-id"


def test_generates_request_id_when_absent():
    client = TestClient(openworld_app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")


def test_structured_401_includes_request_id():
    client = TestClient(openworld_app)
    response = client.post("/api/v1/actions", json={"action": "email.send", "parameters": {}})
    assert response.status_code == 401
    body = response.json()
    assert body["error"] == "unauthorized"
    assert body["request_id"]
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert "detail" in body


def test_security_headers_present():
    client = TestClient(openworld_app)
    response = client.get("/api/v1/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    client = TestClient(openworld_app)
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"


def test_request_body_too_large():
    client = TestClient(_gateway_app(max_body_bytes=16))
    response = client.post("/echo", content=b"x" * 64, headers={"content-type": "application/json"})
    assert response.status_code == 413
    body = response.json()
    assert body["error"] == "payload_too_large"
    assert response.headers.get("X-Request-ID")


def test_response_body_too_large():
    client = TestClient(_gateway_app(max_response_bytes=32))
    response = client.get("/big")
    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "response_too_large"
    assert response.headers.get("X-Request-ID")


def test_rate_limit_hook_returns_429():
    client = TestClient(_gateway_app(rate_limiter=_DenyLimiter()))
    response = client.get("/ok")
    assert response.status_code == 429
    assert response.headers.get("Retry-After") == "9"
    body = response.json()
    assert body["error"] == "rate_limit_exceeded"


def test_structured_error_shape():
    payload = structured_error(status_code=403, message="no", request_id="r1")
    assert payload == {
        "error": "forbidden",
        "message": "no",
        "request_id": "r1",
        "detail": "no",
    }


def test_idempotency_conflict_is_409():
    client = TestClient(openworld_app)
    headers = action_headers("agent-email-bot", idempotency_key="gw-idem-1")
    body = {"action": "email.send", "parameters": {"to": "a@test.com"}, "auto_approve": True}
    first = client.post("/api/v1/actions", json=body, headers=headers)
    assert first.status_code == 200
    second = client.post(
        "/api/v1/actions",
        json={"action": "email.send", "parameters": {"to": "b@test.com"}, "auto_approve": True},
        headers=headers,
    )
    assert second.status_code == 409
    assert second.json()["error"] == "conflict"
