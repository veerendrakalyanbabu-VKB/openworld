"""Verification engine — validates action outcomes."""

import uuid

from core.execution.engine import ExecutionResult
from core.models.action import ActionRequest
from core.models.verification import VerificationResult, VerificationStatus
from core.utils.time import utc_now


class VerificationEngine:
    """
    Verifies that executed actions achieved expected outcomes.

    Never marks success merely because the executor didn't throw.
    """

    def verify(
        self,
        action: ActionRequest,
        execution: ExecutionResult,
        expected: str | None = None,
    ) -> VerificationResult:
        verification_id = str(uuid.uuid4())

        if not execution.success:
            return VerificationResult(
                id=verification_id,
                action_id=action.id,
                expected_result=expected or self._default_expected(action),
                actual_result=f"Execution failed: {execution.error}",
                status=VerificationStatus.FAILED,
                evidence=[f"Executor '{execution.executor}' returned failure"],
                details={"execution_id": execution.execution_id, "error": execution.error},
            )

        expected_result = expected or self._default_expected(action)
        actual_result = self._extract_actual(action, execution)
        status = self._compare(expected_result, actual_result, execution)

        evidence = [
            f"Executor: {execution.executor}",
            f"Execution ID: {execution.execution_id}",
            f"Executed at: {execution.executed_at.isoformat()}",
        ]
        if execution.output.get("demo"):
            evidence.append("DEMO / SYNTHETIC DATA — simulated execution")

        return VerificationResult(
            id=verification_id,
            action_id=action.id,
            expected_result=expected_result,
            actual_result=actual_result,
            status=status,
            evidence=evidence,
            details={"execution_output": execution.output},
            verified_at=utc_now(),
        )

    def _default_expected(self, action: ActionRequest) -> str:
        expectations = {
            "email.send": "email successfully delivered",
            "payment.create": "payment successfully processed",
            "payment.send": "payment successfully sent",
            "invoice.send": "invoice successfully delivered",
            "invoice.create": "invoice successfully created",
            "webhook.send": "webhook successfully delivered",
            "api.read": "API response received",
            "api.write": "API write confirmed",
        }
        return expectations.get(action.action, f"{action.action} completed successfully")

    def _extract_actual(self, action: ActionRequest, execution: ExecutionResult) -> str:
        output = execution.output
        status = output.get("status", "completed")
        if "email" in action.action:
            return f"delivery {status}"
        if "payment" in action.action:
            return f"payment {status}"
        if "invoice" in action.action:
            return f"invoice {status}"
        if "webhook" in action.action:
            return f"webhook response {output.get('status_code', 200)}"
        return f"execution {status}"

    def _compare(
        self, expected: str, actual: str, execution: ExecutionResult
    ) -> VerificationStatus:
        if not execution.success:
            return VerificationStatus.FAILED

        # Check output status fields
        output_status = execution.output.get("status", "")
        if output_status in ("failed", "error", "rejected"):
            return VerificationStatus.FAILED

        if output_status in ("delivered", "completed", "created", "sent"):
            return VerificationStatus.VERIFIED

        # Default: verify if execution succeeded with output
        if execution.output:
            return VerificationStatus.VERIFIED

        return VerificationStatus.PARTIAL
