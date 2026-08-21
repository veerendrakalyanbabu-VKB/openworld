"""OpenWorld API client."""

from typing import Any

import httpx

DEFAULT_OPERATOR_AGENT_ID = "agent-ops-bot"

class OpenWorldClient:
    """Client for the OpenWorld API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
        *,
        token: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._token = token
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def set_token(self, token: str) -> None:
        self._token = token

    def get_demo_token(self, agent_id: str) -> str:
        """Fetch a demo JWT for the given agent (local development only)."""
        response = self._client.get("/api/v1/auth/demo-agents")
        response.raise_for_status()
        for agent in response.json().get("agents", []):
            if agent["agent_id"] == agent_id:
                return agent["access_token"]
        raise ValueError(f"No demo token for agent: {agent_id}")

    def _auth_headers(self, agent_id: str | None = None) -> dict[str, str]:
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        if agent_id:
            return {"Authorization": f"Bearer {self.get_demo_token(agent_id)}"}
        return {}

    def health(self) -> dict[str, Any]:
        response = self._client.get("/api/v1/health")
        response.raise_for_status()
        return response.json()

    def stats(self) -> dict[str, Any]:
        response = self._client.get("/api/v1/stats")
        response.raise_for_status()
        return response.json()

    @property
    def agents(self) -> "AgentsAPI":
        return AgentsAPI(self._client)

    @property
    def actions(self) -> "ActionsAPI":
        return ActionsAPI(self._client, self)

    @property
    def policies(self) -> "PoliciesAPI":
        return PoliciesAPI(self._client)

    @property
    def approvals(self) -> "ApprovalsAPI":
        return ApprovalsAPI(self._client, self)

    @property
    def audit(self) -> "AuditAPI":
        return AuditAPI(self._client, self)

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class AgentsAPI:
    def __init__(self, client: httpx.Client):
        self._client = client

    def list(self, search: str | None = None, status: str | None = None) -> dict[str, Any]:
        params = {}
        if search:
            params["search"] = search
        if status:
            params["status"] = status
        response = self._client.get("/api/v1/agents", params=params)
        response.raise_for_status()
        return response.json()

    def get(self, agent_id: str) -> dict[str, Any]:
        response = self._client.get(f"/api/v1/agents/{agent_id}")
        response.raise_for_status()
        return response.json()


class ActionsAPI:
    def __init__(self, client: httpx.Client, owner: "OpenWorldClient"):
        self._client = client
        self._owner = owner

    def list(self, **params) -> dict[str, Any]:
        response = self._client.get("/api/v1/actions", params=params)
        response.raise_for_status()
        return response.json()

    def get(self, action_id: str) -> dict[str, Any]:
        response = self._client.get(f"/api/v1/actions/{action_id}")
        response.raise_for_status()
        return response.json()

    def request(
        self,
        agent: str,
        action: str,
        parameters: dict | None = None,
        target: str = "",
        auto_approve: bool = False,
    ) -> dict[str, Any]:
        agents = self._client.get("/api/v1/agents").json()["agents"]
        agent_obj = next((a for a in agents if a["name"] == agent or a["id"] == agent), None)
        if not agent_obj:
            raise ValueError(f"Agent not found: {agent}")

        response = self._client.post(
            "/api/v1/actions",
            json={
                "action": action,
                "target": target,
                "parameters": parameters or {},
                "auto_approve": auto_approve,
            },
            headers=self._owner._auth_headers(agent_obj["id"]),
        )
        response.raise_for_status()
        return response.json()

    def simulate(self, agent: str, action: str, parameters: dict | None = None) -> dict[str, Any]:
        agents = self._client.get("/api/v1/agents").json()["agents"]
        agent_obj = next((a for a in agents if a["name"] == agent or a["id"] == agent), None)
        if not agent_obj:
            raise ValueError(f"Agent not found: {agent}")

        response = self._client.post(
            "/api/v1/actions/simulate",
            json={"action": action, "parameters": parameters or {}},
            headers=self._owner._auth_headers(agent_obj["id"]),
        )
        response.raise_for_status()
        return response.json()


class PoliciesAPI:
    def __init__(self, client: httpx.Client):
        self._client = client

    def list(self) -> dict[str, Any]:
        response = self._client.get("/api/v1/policies")
        response.raise_for_status()
        return response.json()


class ApprovalsAPI:
    def __init__(self, client: httpx.Client, owner: "OpenWorldClient"):
        self._client = client
        self._owner = owner

    def list(self, operator_agent_id: str = DEFAULT_OPERATOR_AGENT_ID) -> dict[str, Any]:
        response = self._client.get(
            "/api/v1/approvals",
            headers=self._owner._auth_headers(operator_agent_id),
        )
        response.raise_for_status()
        return response.json()

    def approve(
        self,
        action_id: str,
        *,
        operator_agent_id: str = DEFAULT_OPERATOR_AGENT_ID,
        reason: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if reason:
            body["reason"] = reason
        response = self._client.post(
            f"/api/v1/approvals/{action_id}/approve",
            json=body,
            headers=self._owner._auth_headers(operator_agent_id),
        )
        response.raise_for_status()
        return response.json()

    def deny(
        self,
        action_id: str,
        reason: str = "",
        *,
        operator_agent_id: str = DEFAULT_OPERATOR_AGENT_ID,
    ) -> dict[str, Any]:
        response = self._client.post(
            f"/api/v1/approvals/{action_id}/deny",
            json={"reason": reason},
            headers=self._owner._auth_headers(operator_agent_id),
        )
        response.raise_for_status()
        return response.json()


class AuditAPI:
    def __init__(self, client: httpx.Client, owner: "OpenWorldClient"):
        self._client = client
        self._owner = owner

    def list(
        self,
        *,
        operator_agent_id: str = DEFAULT_OPERATOR_AGENT_ID,
        **params,
    ) -> dict[str, Any]:
        response = self._client.get(
            "/api/v1/audit",
            params=params,
            headers=self._owner._auth_headers(operator_agent_id),
        )
        response.raise_for_status()
        return response.json()
