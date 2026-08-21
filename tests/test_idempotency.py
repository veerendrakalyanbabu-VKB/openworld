"""Durable idempotency tests."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.main import app
from apps.api.state import state
from tests.conftest import action_headers


@pytest.mark.asyncio
async def test_duplicate_idempotency_key_returns_same_result():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        agents = (await client.get("/api/v1/agents")).json()["agents"]
        email_bot = next(a for a in agents if a["name"] == "EmailBot")
        key = str(uuid.uuid4())
        headers = action_headers(email_bot["id"], idempotency_key=key)
        body = {
            "action": "email.send",
            "parameters": {"to": "idem@example.com", "subject": "Idem"},
            "auto_approve": True,
        }

        r1 = await client.post("/api/v1/actions", json=body, headers=headers)
        r2 = await client.post("/api/v1/actions", json=body, headers=headers)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["action"]["id"] == r2.json()["action"]["id"]


@pytest.mark.asyncio
async def test_conflicting_idempotency_key_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        agents = (await client.get("/api/v1/agents")).json()["agents"]
        email_bot = next(a for a in agents if a["name"] == "EmailBot")
        key = str(uuid.uuid4())
        headers = action_headers(email_bot["id"], idempotency_key=key)

        r1 = await client.post(
            "/api/v1/actions",
            json={"action": "email.send", "parameters": {"to": "a@b.com"}, "auto_approve": True},
            headers=headers,
        )
        assert r1.status_code == 200

        r2 = await client.post(
            "/api/v1/actions",
            json={"action": "email.send", "parameters": {"to": "different@b.com"}, "auto_approve": True},
            headers=headers,
        )
        assert r2.status_code == 409


@pytest.mark.asyncio
async def test_different_idempotency_keys_create_different_actions():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        agents = (await client.get("/api/v1/agents")).json()["agents"]
        email_bot = next(a for a in agents if a["name"] == "EmailBot")
        body = {
            "action": "email.send",
            "parameters": {"to": "multi@example.com"},
            "auto_approve": True,
        }

        r1 = await client.post(
            "/api/v1/actions", json=body, headers=action_headers(email_bot["id"])
        )
        r2 = await client.post(
            "/api/v1/actions", json=body, headers=action_headers(email_bot["id"])
        )
        assert r1.json()["action"]["id"] != r2.json()["action"]["id"]


@pytest.mark.asyncio
async def test_idempotency_prevents_duplicate_execution():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        agents = (await client.get("/api/v1/agents")).json()["agents"]
        email_bot = next(a for a in agents if a["name"] == "EmailBot")
        key = str(uuid.uuid4())
        headers = action_headers(email_bot["id"], idempotency_key=key)
        body = {
            "action": "email.send",
            "parameters": {"to": "exec@example.com"},
            "auto_approve": True,
        }
        count_before = state.execution_engine.execution_count

        await client.post("/api/v1/actions", json=body, headers=headers)
        await client.post("/api/v1/actions", json=body, headers=headers)

        assert state.execution_engine.execution_count == count_before + 1
