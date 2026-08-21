"""Deterministic policy engine."""

import fnmatch
import re
from typing import Any

from core.models.action import ActionRequest, PolicyDecision, PolicyDecisionType
from core.models.policy import (
    ConditionOperator,
    Policy,
    PolicyCondition,
    PolicyEffect,
    PolicyRule,
)


class PolicyEngine:
    """
    Deterministic policy evaluation engine.

    LLMs do NOT decide permissions — this engine does.
  """

    def __init__(self, policies: list[Policy] | None = None, default_deny: bool = False):
        self._policies = policies or []
        self._default_deny = default_deny

    def set_policies(self, policies: list[Policy]) -> None:
        self._policies = policies

    def set_default_deny(self, default_deny: bool) -> None:
        self._default_deny = default_deny

    def evaluate(self, action: ActionRequest, agent_name: str = "") -> PolicyDecision:
        """Evaluate all applicable policies and return a decision."""
        agent = agent_name or action.agent_name
        applicable_rules: list[tuple[Policy, PolicyRule]] = []

        for policy in self._policies:
            if not policy.enabled:
                continue
            for rule in policy.rules:
                if self._rule_matches(rule, action, agent):
                    applicable_rules.append((policy, rule))

        if not applicable_rules:
            if self._default_deny:
                return PolicyDecision(
                    decision=PolicyDecisionType.DENY,
                    reasons=["No matching policies — default deny (fail-closed)"],
                )
            return PolicyDecision(
                decision=PolicyDecisionType.ALLOW,
                reasons=["No matching policies — default allow (demo mode)"],
            )

        # Sort by priority (lower = higher priority)
        applicable_rules.sort(key=lambda x: x[1].priority)

        # Deny takes precedence, then require_approval, then allow
        for policy, rule in applicable_rules:
            if rule.effect == PolicyEffect.DENY:
                return PolicyDecision(
                    decision=PolicyDecisionType.DENY,
                    policy_id=policy.id,
                    policy_name=policy.name,
                    rule_id=rule.id,
                    reasons=[f"Denied by policy '{policy.name}' rule '{rule.name or rule.id}'"],
                )

        for policy, rule in applicable_rules:
            if rule.effect == PolicyEffect.REQUIRE_APPROVAL:
                return PolicyDecision(
                    decision=PolicyDecisionType.REQUIRE_APPROVAL,
                    policy_id=policy.id,
                    policy_name=policy.name,
                    rule_id=rule.id,
                    reasons=[
                        f"Approval required by policy '{policy.name}' rule '{rule.name or rule.id}'"
                    ],
                )

        matched = applicable_rules[0]
        policy, rule = matched
        return PolicyDecision(
            decision=PolicyDecisionType.ALLOW,
            policy_id=policy.id,
            policy_name=policy.name,
            rule_id=rule.id,
            reasons=[f"Allowed by policy '{policy.name}' rule '{rule.name or rule.id}'"],
        )

    def _rule_matches(self, rule: PolicyRule, action: ActionRequest, agent: str) -> bool:
        if rule.agent_match and rule.agent_match != "*":
            if not fnmatch.fnmatch(agent, rule.agent_match):
                return False

        if rule.action_match and rule.action_match != "*":
            if not fnmatch.fnmatch(action.action, rule.action_match):
                return False

        if rule.capability_match and rule.capability_match != "*":
            if not any(
                fnmatch.fnmatch(cap, rule.capability_match) for cap in action.requested_permissions
            ):
                return False

        for condition in rule.conditions:
            if not self._evaluate_condition(condition, action):
                return False

        return True

    def _evaluate_condition(self, condition: PolicyCondition, action: ActionRequest) -> bool:
        value = self._resolve_field(condition.field, action)
        expected = condition.value

        if value is None:
            return False

        op = condition.operator
        if op == ConditionOperator.EQ:
            return value == expected
        if op == ConditionOperator.NE:
            return value != expected
        if op == ConditionOperator.GT:
            return self._to_number(value) > self._to_number(expected)
        if op == ConditionOperator.GTE:
            return self._to_number(value) >= self._to_number(expected)
        if op == ConditionOperator.LT:
            return self._to_number(value) < self._to_number(expected)
        if op == ConditionOperator.LTE:
            return self._to_number(value) <= self._to_number(expected)
        if op == ConditionOperator.CONTAINS:
            return str(expected) in str(value)
        if op == ConditionOperator.MATCHES:
            return bool(re.match(str(expected), str(value)))

        return False

    def _resolve_field(self, field: str, action: ActionRequest) -> Any:
        if field.startswith("parameters."):
            key = field[len("parameters.") :]
            return action.parameters.get(key)
        if field.startswith("context."):
            key = field[len("context.") :]
            return action.context.get(key)
        mapping = {
            "agent": action.agent_name,
            "agent_id": action.agent_id,
            "action": action.action,
            "target": action.target,
        }
        return mapping.get(field, action.parameters.get(field))

    def _to_number(self, value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value).replace(",", "").replace("₹", "").replace("$", ""))
        except (ValueError, TypeError):
            return 0.0

    def simulate(
        self, action: ActionRequest, agent_name: str = ""
    ) -> dict:
        """Simulate policy evaluation without side effects."""
        decision = self.evaluate(action, agent_name)
        return {
            "decision": decision.decision.value,
            "policy_id": decision.policy_id,
            "policy_name": decision.policy_name,
            "rule_id": decision.rule_id,
            "reasons": decision.reasons,
            "simulation": True,
        }
