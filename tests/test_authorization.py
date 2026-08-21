"""Authorization boundary tests for Milestone 2.0A."""

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.config import DEFAULT_DEV_SECRET, settings
from apps.api.main import app
from tests.conftest import (
    DEMO_AGENT_EMAIL,
    DEMO_AGENT_FINANCE,
    action_headers,
    auth_header,
    operator_headers,
    policy_admin_headers,
)


@pytest.mark.asyncio
async def test_unauthenticated_approval_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/actions",
            json={"action": "payment.create", "parameters": {"amount": 75000}},
            headers=action_headers(DEMO_AGENT_FINANCE),
        )
        action_id = response.json()["action"]["id"]
        approve = await client.post(f"/api/v1/approvals/{action_id}/approve")
        assert approve.status_code == 401


@pytest.mark.asyncio
async def test_agent_cannot_approve_without_operator_role():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        pending = await client.post(
            "/api/v1/actions",
            json={"action": "payment.create", "parameters": {"amount": 75000}},
            headers=action_headers(DEMO_AGENT_FINANCE),
        )
        action_id = pending.json()["action"]["id"]
        response = await client.post(
            f"/api/v1/approvals/{action_id}/approve",
            json={"approver": "spoofed-human"},
            headers=auth_header(DEMO_AGENT_EMAIL),
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_operator_can_approve_and_identity_not_spoofed():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        pending = await client.post(
            "/api/v1/actions",
            json={"action": "payment.create", "parameters": {"amount": 75000}},
            headers=action_headers(DEMO_AGENT_FINANCE),
        )
        action_id = pending.json()["action"]["id"]
        response = await client.post(
            f"/api/v1/approvals/{action_id}/approve",
            json={"approver": "spoofed-human"},
            headers=operator_headers(),
        )
        assert response.status_code == 200
        assert response.json()["approved_by"] == "agent-ops-bot"
        assert response.json()["action"]["status"] == "verified"


@pytest.mark.asyncio
async def test_unauthenticated_policy_create_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/policies",
            json={"id": "policy-test", "name": "test-policy", "rules": []},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_agent_cannot_create_policy():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/policies",
            json={"id": "policy-agent-test", "name": "agent-policy", "rules": []},
            headers=auth_header(DEMO_AGENT_EMAIL),
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_policy_admin_can_create_policy():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/policies",
            json={"id": "policy-admin-test", "name": "admin-policy", "rules": []},
            headers=policy_admin_headers(),
        )
        assert response.status_code == 200
        assert response.json()["created_by"] == "agent-api-bot"


@pytest.mark.asyncio
async def test_policy_read_remains_public():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/policies")
        assert response.status_code == 200
        assert response.json()["total"] >= 4


@pytest.mark.asyncio
async def test_audit_create_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/audit",
            json={"event_type": "fake"},
            headers=auth_header(DEMO_AGENT_EMAIL),
        )
        assert response.status_code in (404, 405)


@pytest.mark.asyncio
async def test_audit_read_requires_authentication():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/audit")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_audit_read_with_authentication():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/audit", headers=operator_headers())
        assert response.status_code == 200
        assert "events" in response.json()


@pytest.mark.asyncio
async def test_production_config_rejects_sqlite():
    original_demo = settings.demo_mode
    original_db = settings.database_url
    try:
        settings.demo_mode = False
        settings.database_url = "sqlite:///:memory:"
        with pytest.raises(RuntimeError, match="PostgreSQL"):
            settings.validate_production_safety()
    finally:
        settings.demo_mode = original_demo
        settings.database_url = original_db


@pytest.mark.asyncio
async def test_production_config_rejects_default_secret():
    original_demo = settings.demo_mode
    original_secret = settings.secret_key
    try:
        settings.demo_mode = False
        settings.database_url = "postgresql://openworld:pw@localhost:5432/openworld"
        settings.secret_key = DEFAULT_DEV_SECRET
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            settings.validate_production_safety()
    finally:
        settings.demo_mode = original_demo
        settings.secret_key = original_secret
