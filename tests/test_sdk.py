"""SDK client tests against the in-process API gateway."""

import json
import uuid
from unittest.mock import patch

import httpx
import pytest
from starlette.testclient import TestClient

from apps.api.auth.jwt import create_agent_token
from apps.api.main import app
from packages.sdk.openworld.client import OpenWorldClient
from packages.sdk.openworld.exceptions import (
    AuthError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    TimeoutError,
)
from tests.conftest import (
    DEMO_AGENT_EMAIL,
    DEMO_AGENT_FINANCE,
    DEMO_AGENT_OPERATOR,
    DEMO_AGENT_POLICY_ADMIN,
    DEMO_AGENT_SYSTEM_ADMIN,
)

DEMO_AGENT_INVOICE = "agent-invoice-bot"


class _SyncAppTransport(httpx.BaseTransport):
    """Sync transport bridging httpx.Client to Starlette TestClient."""

    def __init__(self):
        self._client = TestClient(app)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        query = request.url.query
        if isinstance(query, bytes):
            query = query.decode()
        path = request.url.path
        if query:
            path = f"{path}?{query}"
        response = self._client.request(
            request.method,
            path,
            content=request.content,
            headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
        )
        return httpx.Response(
            status_code=response.status_code,
            headers=response.headers,
            content=response.content,
            request=request,
        )


@pytest.fixture
def sdk_client():
    transport = _SyncAppTransport()
    with OpenWorldClient(base_url="http://test", transport=transport) as client:
        yield client


def _token(agent_id: str) -> str:
    return create_agent_token(agent_id)


class TestAuth:
    def test_health_no_auth(self, sdk_client):
        result = sdk_client.health()
        assert result.status == "healthy"

    def test_readiness(self, sdk_client):
        result = sdk_client.readiness()
        assert result.status == "ready"
        assert result.database == "connected"

    def test_demo_token_auth(self, sdk_client):
        token = sdk_client.get_demo_token(DEMO_AGENT_EMAIL)
        assert token
        sdk_client.set_token(token)
        result = sdk_client.actions.list()
        assert result.total >= 0

    def test_missing_auth_raises(self, sdk_client):
        with pytest.raises(AuthError) as exc_info:
            sdk_client.approvals.list()
        assert exc_info.value.status_code == 401
        assert exc_info.value.request_id

    def test_invalid_token_raises(self, sdk_client):
        with pytest.raises(AuthError) as exc_info:
            sdk_client.approvals.list(token="invalid-token")
        assert exc_info.value.status_code == 401

    def test_issue_token(self, sdk_client):
        token_resp = sdk_client.get_token(DEMO_AGENT_EMAIL)
        assert token_resp.access_token
        assert token_resp.agent_id == DEMO_AGENT_EMAIL


class TestActions:
    def test_submit_action(self, sdk_client):
        result = sdk_client.actions.submit(
            agent="EmailBot",
            action="email.send",
            parameters={"to": "sdk@test.com", "subject": "SDK Test"},
            auto_approve=True,
            token=_token(DEMO_AGENT_EMAIL),
        )
        assert result.action["status"] == "verified"

    def test_simulate_action(self, sdk_client):
        result = sdk_client.actions.simulate(
            agent="FinanceBot",
            action="payment.create",
            parameters={"amount": 48500},
            token=_token(DEMO_AGENT_FINANCE),
        )
        assert result.simulation is True
        assert "decision" in result.policy

    def test_action_status(self, sdk_client):
        submitted = sdk_client.actions.submit(
            agent="EmailBot",
            action="email.send",
            parameters={"to": "status@test.com"},
            auto_approve=True,
            token=_token(DEMO_AGENT_EMAIL),
        )
        status = sdk_client.actions.status(submitted.action["id"])
        assert status.action["id"] == submitted.action["id"]

    def test_idempotency_same_key(self, sdk_client):
        idem_key = str(uuid.uuid4())
        body_params = {"to": "idem@test.com", "subject": "Idem"}
        r1 = sdk_client.actions.submit(
            agent="EmailBot",
            action="email.send",
            parameters=body_params,
            auto_approve=True,
            idempotency_key=idem_key,
            token=_token(DEMO_AGENT_EMAIL),
        )
        r2 = sdk_client.actions.submit(
            agent="EmailBot",
            action="email.send",
            parameters=body_params,
            auto_approve=True,
            idempotency_key=idem_key,
            token=_token(DEMO_AGENT_EMAIL),
        )
        assert r1.action["id"] == r2.action["id"]

    def test_idempotency_conflict_raises(self, sdk_client):
        idem_key = str(uuid.uuid4())
        sdk_client.actions.submit(
            agent="EmailBot",
            action="email.send",
            parameters={"to": "a@test.com"},
            auto_approve=True,
            idempotency_key=idem_key,
            token=_token(DEMO_AGENT_EMAIL),
        )
        with pytest.raises(ConflictError) as exc_info:
            sdk_client.actions.submit(
                agent="EmailBot",
                action="email.send",
                parameters={"to": "b@test.com"},
                auto_approve=True,
                idempotency_key=idem_key,
                token=_token(DEMO_AGENT_EMAIL),
            )
        assert exc_info.value.status_code == 409


class TestApprovals:
    def test_operator_approve(self, sdk_client):
        pending = sdk_client.actions.submit(
            agent="FinanceBot",
            action="payment.create",
            parameters={"amount": 75000, "recipient": "SDK Vendor"},
            token=_token(DEMO_AGENT_FINANCE),
        )
        action_id = pending.action["id"]
        approved = sdk_client.approvals.approve(
            action_id,
            token=_token(DEMO_AGENT_OPERATOR),
        )
        assert approved.action["status"] == "verified"

    def test_non_operator_forbidden(self, sdk_client):
        pending = sdk_client.actions.submit(
            agent="FinanceBot",
            action="payment.create",
            parameters={"amount": 75000},
            token=_token(DEMO_AGENT_FINANCE),
        )
        with pytest.raises(ForbiddenError) as exc_info:
            sdk_client.approvals.approve(
                pending.action["id"],
                token=_token(DEMO_AGENT_INVOICE),
            )
        assert exc_info.value.status_code == 403


class TestPolicies:
    def test_list_policies(self, sdk_client):
        result = sdk_client.policies.list()
        assert result.total >= 1

    def test_policy_admin_create(self, sdk_client):
        policy_id = f"sdk-policy-{uuid.uuid4().hex[:8]}"
        created = sdk_client.policies.create(
            policy_id,
            "SDK Test Policy",
            token=_token(DEMO_AGENT_POLICY_ADMIN),
        )
        assert created.policy["id"] == policy_id

    def test_non_admin_forbidden(self, sdk_client):
        with pytest.raises(ForbiddenError):
            sdk_client.policies.create(
                f"deny-{uuid.uuid4().hex[:8]}",
                "Should Fail",
                token=_token(DEMO_AGENT_EMAIL),
            )


class TestRoles:
    def test_list_own_roles(self, sdk_client):
        roles = sdk_client.roles.list(DEMO_AGENT_OPERATOR, token=_token(DEMO_AGENT_OPERATOR))
        assert "operator" in roles.roles

    def test_system_admin_assign(self, sdk_client):
        result = sdk_client.roles.assign(
            DEMO_AGENT_EMAIL,
            "operator",
            admin_token=_token(DEMO_AGENT_SYSTEM_ADMIN),
        )
        assert "operator" in result.new_roles

    def test_system_admin_revoke(self, sdk_client):
        sdk_client.roles.assign(
            DEMO_AGENT_EMAIL,
            "operator",
            admin_token=_token(DEMO_AGENT_SYSTEM_ADMIN),
        )
        result = sdk_client.roles.revoke(
            DEMO_AGENT_EMAIL,
            "operator",
            admin_token=_token(DEMO_AGENT_SYSTEM_ADMIN),
        )
        assert "operator" not in result.new_roles

    def test_non_admin_role_assign_forbidden(self, sdk_client):
        with pytest.raises(ForbiddenError) as exc_info:
            sdk_client.roles.assign(
                DEMO_AGENT_EMAIL,
                "operator",
                admin_token=_token(DEMO_AGENT_EMAIL),
            )
        assert exc_info.value.status_code == 403


class TestAudit:
    def test_list_audit(self, sdk_client):
        events = sdk_client.audit.list(token=_token(DEMO_AGENT_OPERATOR), limit=5)
        assert events.total >= 0

    def test_export_audit_json(self, sdk_client):
        content = sdk_client.audit.export(format="json", token=_token(DEMO_AGENT_OPERATOR), limit=5)
        payload = json.loads(content.decode())
        assert "events" in payload

    def test_export_audit_csv(self, sdk_client):
        content = sdk_client.audit.export(format="csv", token=_token(DEMO_AGENT_OPERATOR), limit=5)
        text = content.decode()
        assert "event_type" in text


class TestCorrelationIds:
    def test_client_sends_correlation_id(self, sdk_client):
        corr_id = str(uuid.uuid4())
        sdk_client.set_correlation_id(corr_id)
        sdk_client.health()
        assert sdk_client.last_request_id == corr_id

    def test_response_includes_request_id(self, sdk_client):
        sdk_client.health()
        assert sdk_client.last_request_id


class TestErrors:
    def test_not_found_agent(self, sdk_client):
        with pytest.raises(NotFoundError):
            sdk_client.actions.submit(
                agent="NonExistentBot",
                action="email.send",
                token=_token(DEMO_AGENT_EMAIL),
            )

    def test_timeout_raises(self):
        with (
            patch.object(httpx.Client, "request", side_effect=httpx.TimeoutException("timed out")),
            OpenWorldClient(base_url="http://test", timeout=0.001) as client,
            pytest.raises(TimeoutError),
        ):
            client.health()
