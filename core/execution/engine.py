"""Action execution engine with registered executors."""

import uuid
from abc import ABC, abstractmethod
from typing import Any

from core.models.action import ActionRequest
from core.utils.time import utc_now


class ExecutionResult:
  def __init__(
      self,
      success: bool,
      output: dict[str, Any] | None = None,
      error: str | None = None,
      executor: str = "",
  ):
      self.success = success
      self.output = output or {}
      self.error = error
      self.executor = executor
      self.execution_id = str(uuid.uuid4())
      self.executed_at = utc_now()


class ActionExecutor(ABC):
    """Base class for action executors."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def supported_actions(self) -> list[str]:
        pass

    @abstractmethod
    async def execute(self, action: ActionRequest) -> ExecutionResult:
        pass

    def can_execute(self, action: ActionRequest) -> bool:
        return any(
            action.action == supported or action.action.startswith(supported.rstrip("*"))
            for supported in self.supported_actions
        )


class MockEmailExecutor(ActionExecutor):
    @property
    def name(self) -> str:
        return "mock_email"

    @property
    def supported_actions(self) -> list[str]:
        return ["email.send", "email.*"]

    async def execute(self, action: ActionRequest) -> ExecutionResult:
        to = action.parameters.get("to", action.target)
        subject = action.parameters.get("subject", "No subject")
        return ExecutionResult(
            success=True,
            output={
                "message_id": f"msg-{uuid.uuid4().hex[:12]}",
                "to": to,
                "subject": subject,
                "status": "delivered",
                "demo": True,
            },
            executor=self.name,
        )


class MockWebhookExecutor(ActionExecutor):
    @property
    def name(self) -> str:
        return "mock_webhook"

    @property
    def supported_actions(self) -> list[str]:
        return ["webhook.send", "webhook.*"]

    async def execute(self, action: ActionRequest) -> ExecutionResult:
        url = action.parameters.get("url", action.target)
        return ExecutionResult(
            success=True,
            output={
                "webhook_id": f"wh-{uuid.uuid4().hex[:12]}",
                "url": url,
                "status_code": 200,
                "response": "OK",
                "demo": True,
            },
            executor=self.name,
        )


class MockApiExecutor(ActionExecutor):
    @property
    def name(self) -> str:
        return "mock_api"

    @property
    def supported_actions(self) -> list[str]:
        return ["api.read", "api.write", "api.*"]

    async def execute(self, action: ActionRequest) -> ExecutionResult:
        endpoint = action.parameters.get("endpoint", action.target)
        method = action.parameters.get("method", "GET")
        return ExecutionResult(
            success=True,
            output={
                "request_id": f"req-{uuid.uuid4().hex[:12]}",
                "endpoint": endpoint,
                "method": method,
                "status_code": 200,
                "demo": True,
            },
            executor=self.name,
        )


class MockPaymentExecutor(ActionExecutor):
    @property
    def name(self) -> str:
        return "mock_payment"

    @property
    def supported_actions(self) -> list[str]:
        return ["payment.create", "payment.send", "payment.*"]

    async def execute(self, action: ActionRequest) -> ExecutionResult:
        amount = action.parameters.get("amount", 0)
        recipient = action.parameters.get("recipient", action.target)
        return ExecutionResult(
            success=True,
            output={
                "payment_id": f"pay-{uuid.uuid4().hex[:12]}",
                "amount": amount,
                "recipient": recipient,
                "status": "completed",
                "demo": True,
            },
            executor=self.name,
        )


class MockInvoiceExecutor(ActionExecutor):
    @property
    def name(self) -> str:
        return "mock_invoice"

    @property
    def supported_actions(self) -> list[str]:
        return ["invoice.create", "invoice.send", "invoice.read", "invoice.*"]

    async def execute(self, action: ActionRequest) -> ExecutionResult:
        invoice_id = action.parameters.get("invoice_id", f"INV-{uuid.uuid4().hex[:6].upper()}")
        return ExecutionResult(
            success=True,
            output={
                "invoice_id": invoice_id,
                "status": "delivered" if "send" in action.action else "created",
                "demo": True,
            },
            executor=self.name,
        )


class ExecutionBypassError(PermissionError):
    """Raised when execution is invoked without passing the trust pipeline."""


class ExecutionEngine:
    """Registry and dispatcher for action executors."""

    def __init__(self):
        self._executors: list[ActionExecutor] = []
        self.execution_count: int = 0
        self._register_defaults()

    def reset_execution_count(self) -> None:
        """Reset execution counter (for test isolation)."""
        self.execution_count = 0

    def _register_defaults(self) -> None:
        from core.connectors.github_executor import GitHubIssueExecutor

        for executor in [
            MockEmailExecutor(),
            MockWebhookExecutor(),
            MockApiExecutor(),
            MockPaymentExecutor(),
            MockInvoiceExecutor(),
            GitHubIssueExecutor(),
        ]:
            self.register(executor)

    def register(self, executor: ActionExecutor) -> None:
        self._executors.append(executor)

    def get_executor(self, action: ActionRequest) -> ActionExecutor | None:
        for executor in self._executors:
            if executor.can_execute(action):
                return executor
        return None

    async def execute(
        self,
        action: ActionRequest,
        *,
        pipeline_authorized: bool = False,
    ) -> ExecutionResult:
        if not pipeline_authorized:
            raise ExecutionBypassError(
                "Direct execution is rejected. Actions must pass identity, capability, "
                "policy, and risk gates in ActionLifecycle."
            )
        self.execution_count += 1
        executor = self.get_executor(action)
        if not executor:
            return ExecutionResult(
                success=False,
                error=f"No executor registered for action: {action.action}",
            )
        return await executor.execute(action)

    def list_executors(self) -> list[str]:
        return [e.name for e in self._executors]
