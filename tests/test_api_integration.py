"""Comprehensive API integration tests for trust pipeline."""

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.main import app
from tests.conftest import action_headers, operator_headers


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_stats_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/stats")
        assert response.status_code == 200
        data = response.json()
        assert "active_agents" in data
        assert "demo_mode" in data


@pytest.mark.asyncio
async def test_list_agents():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/agents")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 5
        assert data["demo_mode"] is True


@pytest.mark.asyncio
async def test_list_policies():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/policies")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 4


@pytest.mark.asyncio
async def test_list_verifications():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/verifications")
        assert response.status_code == 200
        data = response.json()
        assert "verifications" in data


@pytest.mark.asyncio
async def test_e2e_allow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        agents = (await client.get("/api/v1/agents")).json()["agents"]
        email_bot = next(a for a in agents if a["name"] == "EmailBot")

        response = await client.post(
            "/api/v1/actions",
            json={
                "action": "email.send",
                "parameters": {"to": "test@example.com", "subject": "Test"},
                "auto_approve": True,
            },
            headers=action_headers(email_bot["id"]),
        )
        assert response.status_code == 200
        action = response.json()["action"]
        assert action["status"] == "verified"
        assert action["policy_decision"]["decision"] == "allow"
        stages = [s["stage"] for s in action["stages"]]
        assert "execution" in stages
        assert "verification" in stages

        audit = (await client.get("/api/v1/audit", headers=operator_headers())).json()["events"]
        assert any(e["event_type"] == "action_executed" for e in audit)


@pytest.mark.asyncio
async def test_e2e_deny():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        agents = (await client.get("/api/v1/agents")).json()["agents"]
        finance_bot = next(a for a in agents if a["name"] == "FinanceBot")

        response = await client.post(
            "/api/v1/actions",
            json={
                "action": "payment.create",
                "parameters": {"amount": 600000},
            },
            headers=action_headers(finance_bot["id"]),
        )
        assert response.status_code == 200
        action = response.json()["action"]
        assert action["status"] == "blocked"
        assert action["policy_decision"]["decision"] == "deny"
        stages = [s["stage"] for s in action["stages"]]
        assert "execution" not in stages

        audit = (await client.get("/api/v1/audit", headers=operator_headers())).json()["events"]
        blocked = [e for e in audit if e["event_type"] == "action_blocked"]
        assert len(blocked) >= 1


@pytest.mark.asyncio
async def test_e2e_require_approval_and_approve():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        agents = (await client.get("/api/v1/agents")).json()["agents"]
        finance_bot = next(a for a in agents if a["name"] == "FinanceBot")

        response = await client.post(
            "/api/v1/actions",
            json={
                "action": "payment.create",
                "parameters": {"amount": 75000, "recipient": "Test Vendor"},
            },
            headers=action_headers(finance_bot["id"]),
        )
        assert response.status_code == 200
        action = response.json()["action"]
        assert action["status"] == "pending_approval"
        action_id = action["id"]

        approvals = (await client.get("/api/v1/approvals", headers=operator_headers())).json()["approvals"]
        assert any(a["id"] == action_id for a in approvals)

        approve_resp = await client.post(
            f"/api/v1/approvals/{action_id}/approve",
            headers=operator_headers(),
        )
        assert approve_resp.status_code == 200
        approved = approve_resp.json()["action"]
        assert approved["status"] == "verified"
        assert "execution" in [s["stage"] for s in approved["stages"]]


@pytest.mark.asyncio
async def test_e2e_require_approval_and_reject():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        agents = (await client.get("/api/v1/agents")).json()["agents"]
        finance_bot = next(a for a in agents if a["name"] == "FinanceBot")

        response = await client.post(
            "/api/v1/actions",
            json={
                "action": "payment.create",
                "parameters": {"amount": 75000, "recipient": "Reject Test"},
            },
            headers=action_headers(finance_bot["id"]),
        )
        action_id = response.json()["action"]["id"]

        deny_resp = await client.post(
            f"/api/v1/approvals/{action_id}/deny",
            json={"reason": "Not authorized"},
            headers=operator_headers(),
        )
        assert deny_resp.status_code == 200
        denied = deny_resp.json()["action"]
        assert denied["status"] == "denied"
        assert "execution" not in [s["stage"] for s in denied["stages"]]


@pytest.mark.asyncio
async def test_simulate_action():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        agents = (await client.get("/api/v1/agents")).json()["agents"]
        finance_bot = next(a for a in agents if a["name"] == "FinanceBot")

        response = await client.post(
            "/api/v1/actions/simulate",
            json={
                "action": "payment.create",
                "parameters": {"amount": 60000},
            },
            headers=action_headers(finance_bot["id"]),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["simulation"] is True
        assert data["policy"]["decision"] == "require_approval"
        assert "identity" in data
        assert "capability" in data
        assert "predicted_outcome" in data


@pytest.mark.asyncio
async def test_audit_events():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/audit", headers=operator_headers())
        assert response.status_code == 200
        data = response.json()
        assert "events" in data


@pytest.mark.asyncio
async def test_capability_catalog():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/capabilities")
        assert response.status_code == 200
        assert response.json()["total"] >= 8


@pytest.mark.asyncio
async def test_agent_create_rejects_wildcard_and_allows_explicit():
    from tests.conftest import system_admin_headers

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        denied = await client.post(
            "/api/v1/agents",
            json={"name": "WildBot", "owner": "qa", "capabilities": ["*"]},
            headers=system_admin_headers(),
        )
        assert denied.status_code == 400

        created = await client.post(
            "/api/v1/agents",
            json={
                "name": "BillingAgent",
                "owner": "billing",
                "organization": "acme",
                "capabilities": ["send_email"],
            },
            headers=system_admin_headers(),
        )
        assert created.status_code == 200
        agent = created.json()["agent"]
        assert agent["capabilities"] == ["email.send"]
        assert agent["organization"] == "acme"
