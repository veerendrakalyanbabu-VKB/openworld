"""OpenWorld API client — thin HTTP wrapper over the gateway."""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from typing import Any

import httpx

from packages.sdk.openworld.exceptions import (
    AuthError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    OpenWorldError,
    TimeoutError,
)
from packages.sdk.openworld.models import (
    ActionListResponse,
    ActionResponse,
    ActionSubmitRequest,
    AgentDetailResponse,
    AgentListResponse,
    ApprovalListResponse,
    ApprovalResponse,
    AuditListResponse,
    DemoAgentsResponse,
    HealthResponse,
    PolicyListResponse,
    PolicyResponse,
    ReadinessResponse,
    RoleListResponse,
    RoleMutationResponse,
    SimulateRequest,
    SimulateResponse,
    StatsResponse,
    TokenResponse,
)

DEFAULT_OPERATOR_AGENT_ID = "agent-ops-bot"


class _HTTPTransport:
    """Internal HTTP layer with error mapping and header support."""

    def __init__(
        self,
        client: httpx.Client,
        *,
        token: str | None = None,
        correlation_id: str | None = None,
    ):
        self._client = client
        self._token = token
        self._correlation_id = correlation_id
        self.last_request_id: str | None = None

    def set_token(self, token: str | None) -> None:
        self._token = token

    def set_correlation_id(self, correlation_id: str | None) -> None:
        self._correlation_id = correlation_id

    @contextlib.contextmanager
    def temporary_token(self, token: str | None) -> Iterator[None]:
        if not token:
            yield
            return
        saved = self._token
        self.set_token(token)
        try:
            yield
        finally:
            self.set_token(saved)

    def _build_headers(
        self,
        headers: dict[str, str] | None = None,
        *,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, str]:
        result = dict(headers or {})
        if self._token:
            result.setdefault("Authorization", f"Bearer {self._token}")
        corr = correlation_id or self._correlation_id
        if corr:
            result.setdefault("X-Request-ID", corr)
        if idempotency_key:
            result["Idempotency-Key"] = idempotency_key
        return result

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, str | int] | None = None,
        headers: dict[str, str] | None = None,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> httpx.Response:
        try:
            response = self._client.request(
                method,
                path,
                json=json,
                params=params,
                headers=self._build_headers(
                    headers,
                    idempotency_key=idempotency_key,
                    correlation_id=correlation_id,
                ),
            )
        except httpx.TimeoutException as exc:
            raise TimeoutError("Request timed out") from exc
        except httpx.RequestError as exc:
            raise OpenWorldError(f"Request failed: {exc}") from exc

        self.last_request_id = response.headers.get("X-Request-ID")
        if response.is_success:
            return response
        self._raise_for_status(response)
        return response  # unreachable

    def _raise_for_status(self, response: httpx.Response) -> None:
        request_id = response.headers.get("X-Request-ID")
        try:
            body = response.json()
        except ValueError:
            body = {}
        message = body.get("message") or body.get("detail") or response.reason_phrase
        if isinstance(message, list):
            message = "; ".join(str(item) for item in message)
        detail = body.get("detail", body)
        kwargs = {
            "status_code": response.status_code,
            "request_id": request_id or body.get("request_id"),
            "detail": detail,
        }
        if response.status_code == 401:
            raise AuthError(str(message), **kwargs)
        if response.status_code == 403:
            raise ForbiddenError(str(message), **kwargs)
        if response.status_code == 404:
            raise NotFoundError(str(message), **kwargs)
        if response.status_code == 409:
            raise ConflictError(str(message), **kwargs)
        raise OpenWorldError(str(message), **kwargs)


class OpenWorldClient:
    """Client for the OpenWorld API gateway.

    The SDK does not evaluate policy, risk, or approval locally.
    All trust decisions remain on the backend.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
        *,
        token: str | None = None,
        correlation_id: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._http_client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            transport=transport,
        )
        self._transport = _HTTPTransport(
            self._http_client,
            token=token,
            correlation_id=correlation_id,
        )

    @property
    def correlation_id(self) -> str | None:
        return self._transport._correlation_id

    @property
    def last_request_id(self) -> str | None:
        return self._transport.last_request_id

    def set_token(self, token: str) -> None:
        self._transport.set_token(token)

    def set_correlation_id(self, correlation_id: str | None) -> None:
        self._transport.set_correlation_id(correlation_id)

    def close(self) -> None:
        with contextlib.suppress(AttributeError):
            self._http_client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # --- Auth ---

    def get_token(self, agent_id: str) -> TokenResponse:
        """Issue a demo JWT (requires demo mode on the API)."""
        response = self._transport.request("POST", "/api/v1/auth/token", json={"agent_id": agent_id})
        return TokenResponse.model_validate(response.json())

    def list_demo_agents(self) -> DemoAgentsResponse:
        response = self._transport.request("GET", "/api/v1/auth/demo-agents")
        return DemoAgentsResponse.model_validate(response.json())

    def get_demo_token(self, agent_id: str) -> str:
        """Fetch a demo JWT for the given agent (local development only)."""
        for agent in self.list_demo_agents().agents:
            if agent.agent_id == agent_id:
                return agent.access_token
        raise NotFoundError(f"No demo token for agent: {agent_id}")

    def authenticate(self, agent_id: str) -> str:
        """Set bearer token from the demo token endpoint and return it."""
        token = self.get_demo_token(agent_id)
        self.set_token(token)
        return token

    # --- Health ---

    def health(self) -> HealthResponse:
        response = self._transport.request("GET", "/api/v1/health")
        return HealthResponse.model_validate(response.json())

    def readiness(self) -> ReadinessResponse:
        response = self._transport.request("GET", "/api/v1/ready")
        return ReadinessResponse.model_validate(response.json())

    def stats(self) -> StatsResponse:
        response = self._transport.request("GET", "/api/v1/stats")
        return StatsResponse.model_validate(response.json())

    # --- Namespaced APIs ---

    @property
    def agents(self) -> AgentsAPI:
        return AgentsAPI(self._transport)

    @property
    def actions(self) -> ActionsAPI:
        return ActionsAPI(self._transport)

    @property
    def policies(self) -> PoliciesAPI:
        return PoliciesAPI(self._transport)

    @property
    def approvals(self) -> ApprovalsAPI:
        return ApprovalsAPI(self._transport)

    @property
    def audit(self) -> AuditAPI:
        return AuditAPI(self._transport)

    @property
    def roles(self) -> RolesAPI:
        return RolesAPI(self._transport)


class AgentsAPI:
    def __init__(self, transport: _HTTPTransport):
        self._transport = transport

    def list(self, search: str | None = None, status: str | None = None) -> AgentListResponse:
        params: dict[str, str | int] = {}
        if search:
            params["search"] = search
        if status:
            params["status"] = status
        response = self._transport.request("GET", "/api/v1/agents", params=params or None)
        return AgentListResponse.model_validate(response.json())

    def get(self, agent_id: str) -> AgentDetailResponse:
        response = self._transport.request("GET", f"/api/v1/agents/{agent_id}")
        return AgentDetailResponse.model_validate(response.json())


class ActionsAPI:
    def __init__(self, transport: _HTTPTransport):
        self._transport = transport

    def list(
        self,
        *,
        agent_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> ActionListResponse:
        params: dict[str, str | int] = {}
        if agent_id:
            params["agent_id"] = agent_id
        if status:
            params["status"] = status
        if limit is not None:
            params["limit"] = limit
        response = self._transport.request("GET", "/api/v1/actions", params=params or None)
        return ActionListResponse.model_validate(response.json())

    def get(self, action_id: str) -> ActionResponse:
        response = self._transport.request("GET", f"/api/v1/actions/{action_id}")
        return ActionResponse.model_validate(response.json())

    def status(self, action_id: str) -> ActionResponse:
        """Alias for get — retrieve action status."""
        return self.get(action_id)

    def _resolve_agent_id(self, agent: str) -> str:
        agents = self._transport.request("GET", "/api/v1/agents").json()["agents"]
        agent_obj = next((a for a in agents if a["name"] == agent or a["id"] == agent), None)
        if not agent_obj:
            raise NotFoundError(f"Agent not found: {agent}")
        return agent_obj["id"]

    def submit(
        self,
        agent: str,
        action: str,
        parameters: dict[str, Any] | None = None,
        *,
        target: str = "",
        auto_approve: bool = False,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
        token: str | None = None,
    ) -> ActionResponse:
        self._resolve_agent_id(agent)
        body = ActionSubmitRequest(
            action=action,
            target=target,
            parameters=parameters or {},
            auto_approve=auto_approve,
        )
        with self._transport.temporary_token(token):
            response = self._transport.request(
                "POST",
                "/api/v1/actions",
                json=body.model_dump(),
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
        return ActionResponse.model_validate(response.json())

    def request(
        self,
        agent: str,
        action: str,
        parameters: dict[str, Any] | None = None,
        target: str = "",
        auto_approve: bool = False,
        **kwargs: Any,
    ) -> ActionResponse:
        """Backward-compatible alias for submit."""
        return self.submit(
            agent,
            action,
            parameters,
            target=target,
            auto_approve=auto_approve,
            **kwargs,
        )

    def simulate(
        self,
        agent: str,
        action: str,
        parameters: dict[str, Any] | None = None,
        *,
        target: str = "",
        token: str | None = None,
    ) -> SimulateResponse:
        self._resolve_agent_id(agent)
        body = SimulateRequest(action=action, target=target, parameters=parameters or {})
        with self._transport.temporary_token(token):
            response = self._transport.request(
                "POST",
                "/api/v1/actions/simulate",
                json=body.model_dump(),
            )
        return SimulateResponse.model_validate(response.json())


class PoliciesAPI:
    def __init__(self, transport: _HTTPTransport):
        self._transport = transport

    def list(self) -> PolicyListResponse:
        response = self._transport.request("GET", "/api/v1/policies")
        return PolicyListResponse.model_validate(response.json())

    def get(self, policy_id: str) -> PolicyResponse:
        response = self._transport.request("GET", f"/api/v1/policies/{policy_id}")
        return PolicyResponse.model_validate(response.json())

    def create(
        self,
        policy_id: str,
        name: str,
        *,
        description: str = "",
        rules: list[dict[str, Any]] | None = None,
        token: str | None = None,
    ) -> PolicyResponse:
        with self._transport.temporary_token(token):
            response = self._transport.request(
                "POST",
                "/api/v1/policies",
                json={"id": policy_id, "name": name, "description": description, "rules": rules or []},
            )
        data = response.json()
        return PolicyResponse(policy=data.get("policy", data), demo_mode=data.get("demo_mode", False))

    def update(
        self,
        policy_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        rules: list[dict[str, Any]] | None = None,
        token: str | None = None,
    ) -> PolicyResponse:
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if rules is not None:
            body["rules"] = rules
        with self._transport.temporary_token(token):
            response = self._transport.request("PUT", f"/api/v1/policies/{policy_id}", json=body)
        data = response.json()
        return PolicyResponse(policy=data.get("policy", data), demo_mode=data.get("demo_mode", False))

    def enable(self, policy_id: str, *, token: str | None = None) -> PolicyResponse:
        return self._mutate(policy_id, "enable", token=token)

    def disable(self, policy_id: str, *, token: str | None = None) -> PolicyResponse:
        return self._mutate(policy_id, "disable", token=token)

    def _mutate(self, policy_id: str, action: str, *, token: str | None = None) -> PolicyResponse:
        with self._transport.temporary_token(token):
            response = self._transport.request("POST", f"/api/v1/policies/{policy_id}/{action}")
        data = response.json()
        return PolicyResponse(policy=data.get("policy", data), demo_mode=data.get("demo_mode", False))


class ApprovalsAPI:
    def __init__(self, transport: _HTTPTransport):
        self._transport = transport

    def list(self, *, token: str | None = None) -> ApprovalListResponse:
        with self._transport.temporary_token(token):
            response = self._transport.request("GET", "/api/v1/approvals")
        return ApprovalListResponse.model_validate(response.json())

    def get(self, action_id: str, *, token: str | None = None) -> ApprovalResponse:
        with self._transport.temporary_token(token):
            response = self._transport.request("GET", f"/api/v1/approvals/{action_id}")
        return ApprovalResponse.model_validate(response.json())

    def approve(
        self,
        action_id: str,
        *,
        reason: str | None = None,
        token: str | None = None,
    ) -> ActionResponse:
        body: dict[str, Any] = {}
        if reason:
            body["reason"] = reason
        with self._transport.temporary_token(token):
            response = self._transport.request(
                "POST",
                f"/api/v1/approvals/{action_id}/approve",
                json=body,
            )
        data = response.json()
        return ActionResponse(action=data.get("action", data), demo_mode=data.get("demo_mode", False))

    def deny(
        self,
        action_id: str,
        reason: str = "",
        *,
        token: str | None = None,
    ) -> ActionResponse:
        with self._transport.temporary_token(token):
            response = self._transport.request(
                "POST",
                f"/api/v1/approvals/{action_id}/deny",
                json={"reason": reason},
            )
        data = response.json()
        return ActionResponse(action=data.get("action", data), demo_mode=data.get("demo_mode", False))


class AuditAPI:
    def __init__(self, transport: _HTTPTransport):
        self._transport = transport

    def list(
        self,
        *,
        token: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        agent: str | None = None,
        event_type: str | None = None,
        decision: str | None = None,
        risk_level: str | None = None,
        subject: str | None = None,
        correlation_id: str | None = None,
    ) -> AuditListResponse:
        params: dict[str, str | int] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if agent:
            params["agent"] = agent
        if event_type:
            params["event_type"] = event_type
        if decision:
            params["decision"] = decision
        if risk_level:
            params["risk_level"] = risk_level
        if subject:
            params["subject"] = subject
        if correlation_id:
            params["correlation_id"] = correlation_id
        with self._transport.temporary_token(token):
            response = self._transport.request("GET", "/api/v1/audit", params=params or None)
        return AuditListResponse.model_validate(response.json())

    def export(
        self,
        *,
        format: str = "json",
        token: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        subject: str | None = None,
        correlation_id: str | None = None,
    ) -> bytes:
        params: dict[str, str | int] = {"format": format}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if subject:
            params["subject"] = subject
        if correlation_id:
            params["correlation_id"] = correlation_id
        with self._transport.temporary_token(token):
            response = self._transport.request("GET", "/api/v1/audit/export", params=params)
        return response.content


class RolesAPI:
    def __init__(self, transport: _HTTPTransport):
        self._transport = transport

    def list(self, agent_id: str, *, token: str | None = None) -> RoleListResponse:
        with self._transport.temporary_token(token):
            response = self._transport.request("GET", f"/api/v1/agents/{agent_id}/roles")
        return RoleListResponse.model_validate(response.json())

    def assign(
        self,
        agent_id: str,
        role: str,
        *,
        admin_token: str | None = None,
    ) -> RoleMutationResponse:
        with self._transport.temporary_token(admin_token):
            response = self._transport.request(
                "POST",
                f"/api/v1/agents/{agent_id}/roles",
                json={"role": role},
            )
        data = response.json()
        return RoleMutationResponse(
            agent_id=data["agent_id"],
            old_roles=data.get("old_roles", []),
            new_roles=data.get("new_roles", []),
            demo_mode=data.get("demo_mode", False),
        )

    def revoke(
        self,
        agent_id: str,
        role_name: str,
        *,
        admin_token: str | None = None,
    ) -> RoleMutationResponse:
        with self._transport.temporary_token(admin_token):
            response = self._transport.request(
                "DELETE",
                f"/api/v1/agents/{agent_id}/roles/{role_name}",
            )
        data = response.json()
        return RoleMutationResponse(
            agent_id=data["agent_id"],
            old_roles=data.get("old_roles", []),
            new_roles=data.get("new_roles", []),
            demo_mode=data.get("demo_mode", False),
        )
