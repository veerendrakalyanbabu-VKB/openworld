"""JWT authentication tests."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_agent_token, decode_agent_token
from apps.api.config import settings
from apps.api.main import app
from tests.conftest import action_headers


@pytest.mark.asyncio
async def test_missing_jwt_returns_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/actions",
            json={"action": "email.send", "parameters": {}},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_valid_jwt_allows_action():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        agents = (await client.get("/api/v1/agents")).json()["agents"]
        email_bot = next(a for a in agents if a["name"] == "EmailBot")
        response = await client.post(
            "/api/v1/actions",
            json={"action": "email.send", "parameters": {"to": "a@b.com"}, "auto_approve": True},
            headers=action_headers(email_bot["id"]),
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_expired_jwt_rejected():
    now = datetime.now(UTC)
    payload = {
        "sub": "agent-email-bot",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
    }
    expired = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/actions",
            json={"action": "email.send", "parameters": {}},
            headers={"Authorization": f"Bearer {expired}"},
        )
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_jwt_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/actions",
            json={"action": "email.send", "parameters": {}},
            headers={"Authorization": "Bearer not-a-valid-token"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_wrong_issuer_rejected():
    now = datetime.now(UTC)
    payload = {
        "sub": "agent-email-bot",
        "iss": "wrong-issuer",
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/actions",
            json={"action": "email.send", "parameters": {}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_unknown_agent_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/actions",
            json={"action": "email.send", "parameters": {}},
            headers={"Authorization": f"Bearer {create_agent_token('nonexistent-agent')}"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_demo_token_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        agents = (await client.get("/api/v1/agents")).json()["agents"]
        email_bot = next(a for a in agents if a["name"] == "EmailBot")
        response = await client.post(
            "/api/v1/auth/token",
            json={"agent_id": email_bot["id"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "DEMO AUTHENTICATION" in data["label"]
        agent_id = decode_agent_token(data["access_token"])
        assert agent_id == email_bot["id"]


@pytest.mark.asyncio
async def test_production_bootstrap_token_issues_jwt(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "auth_bootstrap_token", "test-bootstrap-secret")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/token",
            json={
                "agent_id": "agent-email-bot",
                "bootstrap_token": "test-bootstrap-secret",
            },
        )
        assert response.status_code == 200
        assert decode_agent_token(response.json()["access_token"]) == "agent-email-bot"


@pytest.mark.asyncio
async def test_production_bootstrap_token_rejects_invalid_secret(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "auth_bootstrap_token", "test-bootstrap-secret")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/token",
            json={"agent_id": "agent-email-bot", "bootstrap_token": "wrong"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_production_bootstrap_token_requires_configuration(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "auth_bootstrap_token", "")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/token",
            json={"agent_id": "agent-email-bot"},
        )
        assert response.status_code == 503


@pytest.mark.asyncio
async def test_demo_agents_remains_forbidden_in_production(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/demo-agents")
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthorized_capability_blocked():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        agents = (await client.get("/api/v1/agents")).json()["agents"]
        api_bot = next(a for a in agents if a["name"] == "ApiBot")
        response = await client.post(
            "/api/v1/actions",
            json={
                "action": "database.write",
                "parameters": {"table": "users"},
                "auto_approve": True,
            },
            headers=action_headers(api_bot["id"]),
        )
        assert response.status_code == 200
        action = response.json()["action"]
        assert action["status"] == "blocked"
        assert "execution" not in [s["stage"] for s in action["stages"]]


def test_create_and_decode_token():
    token = create_agent_token("agent-email-bot")
    assert decode_agent_token(token) == "agent-email-bot"
