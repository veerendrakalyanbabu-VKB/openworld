"""Shared pytest fixtures."""

import uuid

import pytest

from apps.api.config import settings
from apps.api.state import state

DEMO_AGENT_EMAIL = "agent-email-bot"
DEMO_AGENT_FINANCE = "agent-finance-bot"
DEMO_AGENT_OPERATOR = "agent-ops-bot"
DEMO_AGENT_POLICY_ADMIN = "agent-api-bot"
DEMO_AGENT_SYSTEM_ADMIN = "agent-admin-bot"


@pytest.fixture(autouse=True)
def reset_state():
    """Reset database and reload demo data before each API test."""
    from core.db import session as db_session

    settings.demo_mode = True
    settings.database_url = "sqlite:///:memory:"
    state._db_initialized = False
    db_session._engine = None
    db_session._SessionLocal = None
    state.init_database()
    state.reset_for_tests()
    state.load_demo_data()
    yield


def auth_header(agent_id: str) -> dict[str, str]:
    from apps.api.auth.jwt import create_agent_token

    return {"Authorization": f"Bearer {create_agent_token(agent_id)}"}


def action_headers(agent_id: str, *, idempotency_key: str | None = None) -> dict[str, str]:
    headers = auth_header(agent_id)
    headers["Idempotency-Key"] = idempotency_key or str(uuid.uuid4())
    return headers


def operator_headers() -> dict[str, str]:
    return auth_header(DEMO_AGENT_OPERATOR)


def policy_admin_headers() -> dict[str, str]:
    return auth_header(DEMO_AGENT_POLICY_ADMIN)


def system_admin_headers() -> dict[str, str]:
    return auth_header(DEMO_AGENT_SYSTEM_ADMIN)
