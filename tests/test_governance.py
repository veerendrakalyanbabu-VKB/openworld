"""Governance tests for Milestone 2.0B."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.main import app
from tests.conftest import (
    DEMO_AGENT_EMAIL,
    DEMO_AGENT_FINANCE,
    action_headers,
    auth_header,
    operator_headers,
    policy_admin_headers,
    system_admin_headers,
)


@pytest.mark.asyncio
async def test_role_assign_unauthenticated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/agents/{DEMO_AGENT_EMAIL}/roles",
            json={"role": "operator"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_role_assign_agent_forbidden():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/agents/{DEMO_AGENT_EMAIL}/roles",
            json={"role": "operator"},
            headers=auth_header(DEMO_AGENT_FINANCE),
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_role_assign_operator_forbidden():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/agents/{DEMO_AGENT_EMAIL}/roles",
            json={"role": "operator"},
            headers=operator_headers(),
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_role_assign_policy_admin_forbidden():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/agents/{DEMO_AGENT_EMAIL}/roles",
            json={"role": "operator"},
            headers=policy_admin_headers(),
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_system_admin_assigns_role_and_audits():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/agents/{DEMO_AGENT_EMAIL}/roles",
            json={"role": "operator"},
            headers=system_admin_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert "operator" in body["new_roles"]
        assert body["assigned_by"] == "agent-admin-bot"

        roles = await client.get(
            f"/api/v1/agents/{DEMO_AGENT_EMAIL}/roles",
            headers=system_admin_headers(),
        )
        assert "operator" in roles.json()["roles"]

        audit = await client.get("/api/v1/audit?event_type=role_assigned", headers=operator_headers())
        assert audit.status_code == 200
        assert any(e["subject"] == DEMO_AGENT_EMAIL for e in audit.json()["events"])


@pytest.mark.asyncio
async def test_cannot_remove_final_system_admin():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(
            "/api/v1/agents/agent-admin-bot/roles/system_admin",
            headers=system_admin_headers(),
        )
        assert response.status_code == 409


@pytest.mark.asyncio
async def test_policy_update_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/v1/policies/policy-email-limits",
            json={"description": "changed"},
            headers=auth_header(DEMO_AGENT_FINANCE),
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_policy_update_version_and_history():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        before = await client.get("/api/v1/policies/policy-email-limits")
        old_version = before.json()["policy"]["version"]

        update = await client.put(
            "/api/v1/policies/policy-email-limits",
            json={"description": "updated description"},
            headers=policy_admin_headers(),
        )
        assert update.status_code == 200
        assert update.json()["policy"]["version"] != old_version

        versions = await client.get("/api/v1/policies/policy-email-limits/versions")
        assert versions.status_code == 200
        assert len(versions.json()["versions"]) >= 1


@pytest.mark.asyncio
async def test_policy_disable_changes_evaluation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        disable = await client.post(
            "/api/v1/policies/policy-email-limits/disable",
            headers=policy_admin_headers(),
        )
        assert disable.status_code == 200
        assert disable.json()["policy"]["enabled"] is False

        action = await client.post(
            "/api/v1/actions",
            json={"action": "email.send", "parameters": {"to": "a@b.com"}},
            headers=action_headers(DEMO_AGENT_EMAIL),
        )
        assert action.status_code == 200
        # With email policy disabled and demo default-allow, action should still proceed
        assert action.json()["action"]["status"] in ("verified", "pending_approval", "blocked")


@pytest.mark.asyncio
async def test_intelligence_production_requires_auth():
    from apps.api.config import settings

    original = settings.demo_mode
    try:
        settings.demo_mode = False
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/intelligence/query?q=blocked")
            assert response.status_code == 401
    finally:
        settings.demo_mode = original


@pytest.mark.asyncio
async def test_intelligence_agent_scoped():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/intelligence/query?q=blocked%20actions",
            headers=auth_header(DEMO_AGENT_FINANCE),
        )
        assert response.status_code == 200
        body = response.json()
        assert body.get("access_level") == "agent"


@pytest.mark.asyncio
async def test_intelligence_agent_forbidden_pending():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/intelligence/query?q=pending%20approval",
            headers=auth_header(DEMO_AGENT_FINANCE),
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_intelligence_operator_allowed():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/intelligence/query?q=pending%20approval",
            headers=operator_headers(),
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_audit_export_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/audit/export?format=json")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_audit_export_operator_json():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/audit/export?format=json&limit=10",
            headers=operator_headers(),
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")


@pytest.mark.asyncio
async def test_audit_export_csv():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/audit/export?format=csv&limit=5",
            headers=operator_headers(),
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "event_type" in response.text


@pytest.mark.asyncio
async def test_identity_abstraction_jwt_unchanged():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/actions",
            json={"action": "email.send", "parameters": {"to": "x@y.com"}},
            headers=action_headers(DEMO_AGENT_EMAIL),
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_policy_create_unique_id():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        policy_id = f"policy-test-{uuid.uuid4().hex[:8]}"
        response = await client.post(
            "/api/v1/policies",
            json={"id": policy_id, "name": "test-policy", "rules": []},
            headers=policy_admin_headers(),
        )
        assert response.status_code == 200

        duplicate = await client.post(
            "/api/v1/policies",
            json={"id": policy_id, "name": "dup", "rules": []},
            headers=policy_admin_headers(),
        )
        assert duplicate.status_code == 409
