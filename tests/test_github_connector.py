"""Bounded GitHub issue connector tests.

Live GitHub calls are NOT claimed here. Default config is disabled (dry-run).
HTTP success is proven with a mock transport only.
"""

from __future__ import annotations

import httpx
import pytest

from core.audit.logger import AuditLogger
from core.connectors.github_executor import GitHubIssueExecutor
from core.connectors.github_issues import GitHubIssuesConnector
from core.connectors.settings import GitHubConnectorConfig
from core.demo.seed import DEMO_AGENTS, DEMO_POLICIES
from core.execution.engine import ExecutionEngine
from core.execution.lifecycle import ActionLifecycle
from core.identity.validator import IdentityValidator
from core.models.action import ActionStatus
from core.permissions.validator import PermissionValidator
from core.policies.engine import PolicyEngine
from core.risk.engine import RiskEngine
from core.verification.engine import VerificationEngine


def _agents():
    return {a.id: a for a in DEMO_AGENTS}


def _lifecycle(engine: ExecutionEngine | None = None):
    execution_engine = engine or ExecutionEngine()
    lifecycle = ActionLifecycle(
        policy_engine=PolicyEngine(DEMO_POLICIES),
        risk_engine=RiskEngine(),
        execution_engine=execution_engine,
        verification_engine=VerificationEngine(),
        audit_logger=AuditLogger(),
        identity_validator=IdentityValidator(),
        permission_validator=PermissionValidator(),
        agent_resolver=lambda aid: _agents().get(aid),
    )
    return lifecycle, execution_engine, lifecycle.audit_logger


class TestGitHubConnectorValidation:
    def test_rejects_arbitrary_url_field(self):
        connector = GitHubIssuesConnector(GitHubConnectorConfig())
        with pytest.raises(Exception, match="Unsupported fields"):
            connector.validate_parameters(
                {"title": "x", "url": "https://evil.example/repos/a/b/issues"}
            )

    def test_rejects_owner_repo_in_payload(self):
        connector = GitHubIssuesConnector(GitHubConnectorConfig())
        with pytest.raises(Exception, match="Unsupported fields"):
            connector.validate_parameters({"title": "x", "owner": "other", "repo": "secret"})

    def test_rejects_empty_title(self):
        connector = GitHubIssuesConnector(GitHubConnectorConfig())
        with pytest.raises(Exception, match="title"):
            connector.validate_parameters({"title": "  "})


class TestGitHubDryRun:
    @pytest.mark.asyncio
    async def test_disabled_connector_is_dry_run(self):
        connector = GitHubIssuesConnector(GitHubConnectorConfig(enabled=False))
        action = ActionRequestStub("github.issue.create", {"title": "Hello"})
        result = await connector.run(action)
        assert result.success is True
        assert result.dry_run is True
        assert result.live is False
        assert result.output["live_verified"] is False
        assert "token" not in str(result.output).lower()


class TestGitHubTrustCore:
    @pytest.mark.asyncio
    async def test_missing_capability_does_not_execute(self):
        lifecycle, engine, _ = _lifecycle()
        agent = _agents()["agent-email-bot"]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action="github.issue.create",
            parameters={"title": "Should not run"},
        )
        result = await lifecycle.process(action, agent=agent, auto_approve=True)
        assert result.status == ActionStatus.BLOCKED
        assert engine.execution_count == 0

    @pytest.mark.asyncio
    async def test_authorized_dry_run_executes_once(self):
        lifecycle, engine, audit = _lifecycle()
        agent = _agents()["agent-github-bot"]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action="github.issue.create",
            parameters={"title": "Bounded issue"},
        )
        result = await lifecycle.process(action, agent=agent, auto_approve=True)
        assert result.status == ActionStatus.VERIFIED
        assert engine.execution_count == 1
        assert result.execution_result["dry_run"] is True
        types = [e.event_type.value for e in audit.get_events()]
        assert "action_executed" in types
        assert "verification_completed" in types


class TestGitHubMockLiveHttp:
    @pytest.mark.asyncio
    async def test_mocked_github_post_uses_allowlisted_host(self):
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            assert request.url.host == "api.github.com"
            assert request.url.path == "/repos/acme/openworld/issues"
            assert request.method == "POST"
            auth = request.headers.get("authorization", "")
            assert auth == "Bearer secret-token"
            return httpx.Response(
                201,
                json={"number": 17, "html_url": "https://github.com/acme/openworld/issues/17"},
            )

        config = GitHubConnectorConfig(
            enabled=True,
            token="secret-token",
            owner="acme",
            repo="openworld",
            timeout_seconds=5,
        )
        connector = GitHubIssuesConnector(config, transport=httpx.MockTransport(handler))
        engine = ExecutionEngine()
        engine._executors = [GitHubIssueExecutor(connector)]
        lifecycle, _, _ = _lifecycle(engine)
        agent = _agents()["agent-github-bot"]
        action = lifecycle.create_action(
            agent_id=agent.id,
            agent_name=agent.name,
            action="github.issue.create",
            parameters={"title": "Mock issue", "body": "from tests"},
        )
        result = await lifecycle.process(action, agent=agent, auto_approve=True)
        assert result.status == ActionStatus.VERIFIED
        assert result.execution_result["issue_number"] == 17
        assert result.execution_result["live"] is True
        assert result.execution_result["live_verified"] is False
        assert "secret-token" not in str(result.execution_result)
        assert len(seen) == 1

    @pytest.mark.asyncio
    async def test_timeout_fails_verification(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("slow")

        config = GitHubConnectorConfig(
            enabled=True,
            token="secret-token",
            owner="acme",
            repo="openworld",
        )
        connector = GitHubIssuesConnector(config, transport=httpx.MockTransport(handler))
        executor = GitHubIssueExecutor(connector)
        action = ActionRequestStub("github.issue.create", {"title": "t"})
        execution = await executor.execute(action)
        assert execution.success is False
        assert "timed out" in (execution.error or "").lower()
        assert "secret-token" not in str(execution.output)
        assert "secret-token" not in str(execution.error)


class ActionRequestStub:
    def __init__(self, action: str, parameters: dict):
        self.action = action
        self.parameters = parameters
        self.target = ""
        self.id = "action-stub"
