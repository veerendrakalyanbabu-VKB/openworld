"""Action lifecycle orchestrator."""

import uuid
from collections.abc import Callable

from core.audit.logger import AuditLogger
from core.execution.engine import ExecutionEngine
from core.identity.validator import IdentityValidator
from core.models.action import (
    ActionRequest,
    ActionStage,
    ActionStageRecord,
    ActionStatus,
    PolicyDecisionType,
)
from core.models.agent import Agent
from core.models.audit import AuditEventType
from core.permissions.validator import PermissionValidator
from core.policies.engine import PolicyEngine
from core.risk.engine import RiskEngine
from core.utils.time import utc_now
from core.verification.engine import VerificationEngine


class ActionLifecycle:
    """
    Orchestrates the full action lifecycle:
    REQUEST → IDENTITY → CAPABILITY → POLICY → RISK → DECISION → APPROVAL → EXECUTE → VERIFY → AUDIT

    DECISION ≠ EXECUTION — execution only occurs after all gates pass.
    """

    def __init__(
        self,
        policy_engine: PolicyEngine,
        risk_engine: RiskEngine,
        execution_engine: ExecutionEngine,
        verification_engine: VerificationEngine,
        audit_logger: AuditLogger,
        identity_validator: IdentityValidator | None = None,
        permission_validator: PermissionValidator | None = None,
        agent_resolver: Callable[[str], Agent | None] | None = None,
    ):
        self.policy_engine = policy_engine
        self.risk_engine = risk_engine
        self.execution_engine = execution_engine
        self.verification_engine = verification_engine
        self.audit_logger = audit_logger
        self.identity_validator = identity_validator or IdentityValidator()
        self.permission_validator = permission_validator or PermissionValidator()
        self.agent_resolver = agent_resolver
        self._pending_approvals: dict[str, ActionRequest] = {}

    def create_action(
        self,
        agent_id: str,
        agent_name: str,
        action: str,
        target: str = "",
        parameters: dict | None = None,
        context: dict | None = None,
        requested_permissions: list[str] | None = None,
    ) -> ActionRequest:
        correlation_id = str(uuid.uuid4())
        action_request = ActionRequest(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            agent_name=agent_name,
            action=action,
            target=target,
            parameters=parameters or {},
            context=context or {},
            requested_permissions=requested_permissions or [action],
            correlation_id=correlation_id,
        )
        action_request.stages.append(
            ActionStageRecord(
                stage=ActionStage.REQUESTED,
                status="completed",
                details={"action": action, "target": target},
            )
        )
        return action_request

    def _audit(
        self,
        event_type: AuditEventType,
        action: ActionRequest,
        *,
        actor: str = "",
        decision: str = "",
        policy_id: str | None = None,
        risk_level: str | None = None,
        details: dict | None = None,
        evidence: list[str] | None = None,
        final_outcome: str = "",
        reason: str = "",
    ) -> None:
        """Create enriched audit record with full trust chain context."""
        enriched_details = {
            "agent_id": action.agent_id,
            "action_type": action.action,
            "requested_capability": action.requested_permissions[0] if action.requested_permissions else action.action,
            "execution_status": action.status.value,
            "verification_status": "pending",
            "final_outcome": final_outcome or action.status.value,
            "reason": reason,
            **(details or {}),
        }
        if action.policy_decision:
            enriched_details["policy_evaluated"] = action.policy_decision.policy_name
        if action.risk_level:
            enriched_details["risk_level"] = action.risk_level
        if action.verification_id:
            enriched_details["verification_status"] = "completed"

        self.audit_logger.log(
            event_type=event_type,
            actor=actor or action.agent_name,
            subject=action.id,
            action=action.action,
            decision=decision,
            policy_id=policy_id,
            risk_level=risk_level or action.risk_level,
            correlation_id=action.correlation_id,
            details=enriched_details,
            evidence=evidence or [],
        )

    async def process(
        self,
        action: ActionRequest,
        agent: Agent | None = None,
        auto_approve: bool = False,
    ) -> ActionRequest:
        """Process action through the full trust lifecycle."""
        if agent is None and self.agent_resolver:
            agent = self.agent_resolver(action.agent_id)

        self._audit(
            AuditEventType.ACTION_REQUESTED,
            action,
            details={"target": action.target, "parameters": action.parameters},
        )

        # ── IDENTITY ──
        if agent is None:
            action.status = ActionStatus.BLOCKED
            action.stages.append(
                ActionStageRecord(
                    stage=ActionStage.IDENTITY,
                    status="failed",
                    details={"error": "Agent not found"},
                )
            )
            action.stages.append(ActionStageRecord(stage=ActionStage.COMPLETE, status="blocked"))
            self._audit(
                AuditEventType.ACTION_BLOCKED,
                action,
                actor="identity_validator",
                decision="deny",
                reason="Unknown agent",
                final_outcome="blocked",
            )
            action.updated_at = utc_now()
            return action

        identity = self.identity_validator.validate(agent)
        if not identity.valid:
            action.status = ActionStatus.BLOCKED
            action.stages.append(
                ActionStageRecord(
                    stage=ActionStage.IDENTITY,
                    status="failed",
                    details={"reasons": identity.reasons},
                    evidence=identity.reasons,
                )
            )
            action.stages.append(ActionStageRecord(stage=ActionStage.COMPLETE, status="blocked"))
            self._audit(
                AuditEventType.ACTION_BLOCKED,
                action,
                actor="identity_validator",
                decision="deny",
                reason=identity.reasons[0] if identity.reasons else "Identity validation failed",
                final_outcome="blocked",
                evidence=identity.reasons,
            )
            action.updated_at = utc_now()
            return action

        action.status = ActionStatus.IDENTITY_VERIFIED
        action.stages.append(
            ActionStageRecord(
                stage=ActionStage.IDENTITY,
                status="verified",
                evidence=identity.reasons,
            )
        )

        # ── CAPABILITY / PERMISSION ──
        permission = self.permission_validator.validate(
            agent, action.action, action.requested_permissions
        )
        if not permission.permitted:
            action.status = ActionStatus.BLOCKED
            action.stages.append(
                ActionStageRecord(
                    stage=ActionStage.POLICY,
                    status="capability_denied",
                    details={
                        "missing_capabilities": permission.missing_capabilities,
                        "reasons": permission.reasons,
                    },
                    evidence=permission.reasons,
                )
            )
            action.stages.append(ActionStageRecord(stage=ActionStage.COMPLETE, status="blocked"))
            self._audit(
                AuditEventType.ACTION_BLOCKED,
                action,
                actor="permission_validator",
                decision="deny",
                reason=permission.reasons[0] if permission.reasons else "Missing capability",
                final_outcome="blocked",
                evidence=permission.reasons,
                details={"missing_capabilities": permission.missing_capabilities},
            )
            action.updated_at = utc_now()
            return action

        # ── POLICY ──
        decision = self.policy_engine.evaluate(action, action.agent_name)
        action.policy_decision = decision
        action.status = ActionStatus.POLICY_EVALUATED
        action.stages.append(
            ActionStageRecord(
                stage=ActionStage.POLICY,
                status=decision.decision.value,
                details={
                    "policy_id": decision.policy_id,
                    "policy_name": decision.policy_name,
                    "reasons": decision.reasons,
                },
            )
        )

        self._audit(
            AuditEventType.POLICY_EVALUATED,
            action,
            actor="policy_engine",
            decision=decision.decision.value,
            policy_id=decision.policy_id,
            evidence=decision.reasons,
        )

        if decision.decision == PolicyDecisionType.DENY:
            action.status = ActionStatus.BLOCKED
            action.stages.append(ActionStageRecord(stage=ActionStage.COMPLETE, status="blocked"))
            self._audit(
                AuditEventType.ACTION_BLOCKED,
                action,
                actor="policy_engine",
                decision="deny",
                policy_id=decision.policy_id,
                reason=decision.reasons[0] if decision.reasons else "Policy denied",
                final_outcome="blocked",
            )
            action.updated_at = utc_now()
            return action

        # ── RISK ──
        reliability = agent.trust_dimensions.reliability if agent else 95.0
        risk = self.risk_engine.assess(action, historical_reliability=reliability)
        action.risk_score = risk.risk_score
        action.risk_level = risk.risk_level.value
        action.stages.append(
            ActionStageRecord(
                stage=ActionStage.RISK,
                status=risk.risk_level.value,
                details={
                    "risk_score": risk.risk_score,
                    "reasons": risk.reasons,
                    "factors": risk.factors,
                    "recommended_decision": risk.recommended_decision,
                },
            )
        )

        self._audit(
            AuditEventType.RISK_ASSESSED,
            action,
            actor="risk_engine",
            risk_level=risk.risk_level.value,
            details={"risk_score": risk.risk_score, "reasons": risk.reasons},
        )

        # Risk-based deny — CRITICAL risk blocks execution
        if risk.recommended_decision == "deny":
            action.status = ActionStatus.BLOCKED
            action.stages.append(ActionStageRecord(stage=ActionStage.COMPLETE, status="blocked"))
            self._audit(
                AuditEventType.ACTION_BLOCKED,
                action,
                actor="risk_engine",
                decision="deny",
                risk_level=risk.risk_level.value,
                reason=f"Risk level {risk.risk_level.value} — execution denied",
                final_outcome="blocked",
                evidence=risk.reasons,
            )
            action.updated_at = utc_now()
            return action

        # ── APPROVAL GATE ──
        needs_approval = (
            decision.decision == PolicyDecisionType.REQUIRE_APPROVAL
            or risk.recommended_decision == "require_approval"
        )

        if needs_approval and not auto_approve:
            action.status = ActionStatus.PENDING_APPROVAL
            action.stages.append(
                ActionStageRecord(stage=ActionStage.APPROVAL, status="pending")
            )
            self._pending_approvals[action.id] = action
            self._audit(
                AuditEventType.APPROVAL_REQUESTED,
                action,
                risk_level=risk.risk_level.value,
                decision="require_approval",
                final_outcome="pending_approval",
            )
            action.updated_at = utc_now()
            return action

        # ── EXECUTE → VERIFY ──
        return await self._execute_and_verify(action)

    async def approve(self, action_id: str, approver: str = "human") -> ActionRequest | None:
        action = self._pending_approvals.get(action_id)
        if not action:
            return None

        action.status = ActionStatus.APPROVED
        for stage in action.stages:
            if stage.stage == ActionStage.APPROVAL:
                stage.status = "approved"
                stage.details["approver"] = approver

        self._audit(
            AuditEventType.APPROVAL_GRANTED,
            action,
            actor=approver,
            decision="approved",
            final_outcome="approved",
        )

        del self._pending_approvals[action_id]
        return await self._execute_and_verify(action)

    async def deny(self, action_id: str, denier: str = "human", reason: str = "") -> ActionRequest | None:
        action = self._pending_approvals.get(action_id)
        if not action:
            return None

        action.status = ActionStatus.DENIED
        for stage in action.stages:
            if stage.stage == ActionStage.APPROVAL:
                stage.status = "denied"
                stage.details["denier"] = denier
                stage.details["reason"] = reason

        self._audit(
            AuditEventType.APPROVAL_DENIED,
            action,
            actor=denier,
            decision="denied",
            reason=reason or "Human rejected approval",
            final_outcome="denied",
            details={"reason": reason},
        )

        action.stages.append(ActionStageRecord(stage=ActionStage.COMPLETE, status="denied"))
        del self._pending_approvals[action_id]
        action.updated_at = utc_now()
        return action

    async def _execute_and_verify(self, action: ActionRequest) -> ActionRequest:
        """Execute and verify — only called after all gates pass."""
        action.status = ActionStatus.EXECUTING
        result = await self.execution_engine.execute(action)

        if result.success:
            action.status = ActionStatus.EXECUTED
            action.execution_result = result.output
            action.stages.append(
                ActionStageRecord(
                    stage=ActionStage.EXECUTION,
                    status="completed",
                    details={**result.output, "demo": True, "executor": result.executor},
                    evidence=[f"DEMO/SYNTHETIC execution via {result.executor}"],
                )
            )
            self._audit(
                AuditEventType.ACTION_EXECUTED,
                action,
                decision="executed",
                final_outcome="executed",
                details={"output": result.output, "demo": True, "executor": result.executor},
            )
        else:
            action.status = ActionStatus.FAILED
            action.stages.append(
                ActionStageRecord(
                    stage=ActionStage.EXECUTION,
                    status="failed",
                    details={"error": result.error},
                )
            )
            self._audit(
                AuditEventType.ACTION_BLOCKED,
                action,
                actor="execution_engine",
                decision="failed",
                reason=result.error or "Execution failed",
                final_outcome="failed",
                details={"error": result.error},
            )
            action.stages.append(ActionStageRecord(stage=ActionStage.COMPLETE, status="failed"))
            action.updated_at = utc_now()
            return action

        verification = self.verification_engine.verify(action, result)
        action.verification_id = verification.id
        action.stages.append(
            ActionStageRecord(
                stage=ActionStage.VERIFICATION,
                status=verification.status.value,
                details={
                    "expected": verification.expected_result,
                    "actual": verification.actual_result,
                },
                evidence=verification.evidence,
            )
        )

        if verification.status.value == "verified":
            action.status = ActionStatus.VERIFIED

        self._audit(
            AuditEventType.VERIFICATION_COMPLETED,
            action,
            actor="verification_engine",
            decision=verification.status.value,
            final_outcome=verification.status.value,
            evidence=verification.evidence,
            details={"verification_id": verification.id},
        )

        action.stages.append(
            ActionStageRecord(stage=ActionStage.COMPLETE, status=action.status.value)
        )
        action.updated_at = utc_now()
        return action

    def get_pending_approvals(self) -> list[ActionRequest]:
        return list(self._pending_approvals.values())

    def get_approval(self, action_id: str) -> ActionRequest | None:
        return self._pending_approvals.get(action_id)

    def reset(self) -> None:
        """Clear pending approvals (for test isolation)."""
        self._pending_approvals.clear()
