"""ExecutionEngine adapter for the GitHub issues connector."""

from core.connectors.base import ConnectorTimeoutError
from core.connectors.github_issues import GitHubIssuesConnector
from core.execution.engine import ActionExecutor, ExecutionResult
from core.models.action import ActionRequest


class GitHubIssueExecutor(ActionExecutor):
    def __init__(self, connector: GitHubIssuesConnector | None = None):
        self._connector = connector or GitHubIssuesConnector()

    @property
    def name(self) -> str:
        return self._connector.name

    @property
    def supported_actions(self) -> list[str]:
        return [self._connector.action]

    async def execute(self, action: ActionRequest) -> ExecutionResult:
        try:
            result = await self._connector.run(action)
        except ConnectorTimeoutError as exc:
            return ExecutionResult(success=False, error=str(exc), executor=self.name)
        return ExecutionResult(
            success=result.success,
            output=result.output,
            error=result.error,
            executor=self.name,
        )
