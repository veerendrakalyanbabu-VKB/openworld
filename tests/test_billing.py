"""Monetization foundation tests — commercial limits, not Trust Core bypass."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm.attributes import flag_modified

from apps.api.main import app
from core.billing.catalog import DEFAULT_ACCOUNT_ID
from core.billing.provider import NoopBillingProvider
from core.db.billing_repositories import BillingAccountRepository
from core.db.session import session_scope
from tests.conftest import DEMO_AGENT_EMAIL, action_headers, system_admin_headers


@pytest.mark.asyncio
async def test_catalog_has_no_live_payments():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/billing/catalog")
        assert response.status_code == 200
        data = response.json()
        assert data["live"] is False
        assert data["payments"] == "BILLING-READY"
        assert data["pricing"] is None
        ids = {item["plan_id"] for item in data["catalog"]}
        assert ids == {"free", "pro", "team", "enterprise"}


@pytest.mark.asyncio
async def test_agent_cannot_change_plan():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/billing/plan",
            json={"plan_id": "enterprise"},
            headers=action_headers(DEMO_AGENT_EMAIL),
        )
        assert response.status_code == 403
        snap = await client.get("/api/v1/billing/account", headers=action_headers(DEMO_AGENT_EMAIL))
        assert snap.json()["plan_id"] == "free"


@pytest.mark.asyncio
async def test_system_admin_can_change_plan_without_payment():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/billing/plan",
            json={"plan_id": "pro"},
            headers=system_admin_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["plan_id"] == "pro"
        assert body["live"] is False
        account = await client.get("/api/v1/billing/account", headers=system_admin_headers())
        assert account.json()["plan_id"] == "pro"


@pytest.mark.asyncio
async def test_quota_blocks_before_trust_core_execution():
    with session_scope() as session:
        account = BillingAccountRepository(session).get(DEFAULT_ACCOUNT_ID)
        assert account is not None
        ents = dict(account.entitlements)
        ents["max_actions_per_month"] = 0
        account.entitlements = ents
        flag_modified(account, "entitlements")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/actions",
            json={"action": "email.send", "parameters": {"to": "a@b.c"}},
            headers=action_headers(DEMO_AGENT_EMAIL),
        )
        assert response.status_code == 403
        assert "entitlement" in str(response.json()).lower()


@pytest.mark.asyncio
async def test_usage_dedup_does_not_double_count():
    from apps.api.state import state

    state.billing.record_action("src-one")
    first = state.billing.snapshot()["usage"]["count"]
    state.billing.record_action("src-one")
    second = state.billing.snapshot()["usage"]["count"]
    assert second == first


def test_noop_provider_never_claims_live_charge():
    provider = NoopBillingProvider()
    result = provider.create_subscription("acct-default", "pro")
    assert result["live"] is False
    assert result["status"] == "not_configured"
    assert "success" not in result.get("message", "").lower()
