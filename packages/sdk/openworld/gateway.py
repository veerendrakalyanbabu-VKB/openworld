"""Minimal developer gateway API over OpenWorldClient."""

from __future__ import annotations

from typing import Any

from packages.sdk.openworld.client import OpenWorldClient
from packages.sdk.openworld.models import ActionResponse


class AgentGateway:
    """Place OpenWorld between an agent and an external action.

    Example:

        gateway = AgentGateway(agent="EmailBot", policy="policy-email-limits")
        result = gateway.execute(
            action="send_email",
            recipient="customer@example.com",
            purpose="invoice_delivery",
        )
    """

    def __init__(
        self,
        agent: str,
        policy: str | None = None,
        *,
        base_url: str = "http://localhost:8000",
        token: str | None = None,
        auto_approve: bool = False,
        client: OpenWorldClient | None = None,
    ):
        self.agent = agent
        self.policy = policy
        self.auto_approve = auto_approve
        self._owns_client = client is None
        self._client = client or OpenWorldClient(base_url=base_url, token=token)
        if token:
            self._client.set_token(token)

    def _ensure_auth(self) -> None:
        if self._client._transport._token:
            return
        agents = self._client.agents.list().agents
        match = next((a for a in agents if a.name == self.agent or a.id == self.agent), None)
        agent_id = match.id if match else self.agent
        self._client.authenticate(agent_id)

    def execute(
        self,
        action: str,
        *,
        recipient: str | None = None,
        purpose: str | None = None,
        auto_approve: bool | None = None,
        idempotency_key: str | None = None,
        **parameters: Any,
    ) -> ActionResponse:
        self._ensure_auth()
        params = dict(parameters)
        if recipient:
            params.setdefault("to", recipient)
            params.setdefault("recipient", recipient)
        if purpose:
            params.setdefault("purpose", purpose)
        if self.policy:
            params.setdefault("policy", self.policy)
        return self._client.actions.submit(
            agent=self.agent,
            action=action,
            parameters=params,
            target=recipient or "",
            auto_approve=self.auto_approve if auto_approve is None else auto_approve,
            idempotency_key=idempotency_key,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> AgentGateway:
        return self

    def __exit__(self, *args) -> None:
        self.close()
