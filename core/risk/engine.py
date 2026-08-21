"""Explainable rule-based risk engine."""

from core.models.action import ActionRequest
from core.models.risk import RiskAssessment, RiskLevel

# Action sensitivity mapping
ACTION_SENSITIVITY: dict[str, float] = {
    "payment.create": 80,
    "payment.send": 85,
    "email.send": 30,
    "invoice.create": 50,
    "invoice.read": 15,
    "invoice.send": 40,
    "api.write": 60,
    "api.read": 20,
    "database.write": 70,
    "database.read": 25,
    "webhook.send": 35,
    "github.issue.create": 45,
    "file.write": 45,
    "file.read": 10,
}

DEFAULT_SENSITIVITY = 40


class RiskEngine:
    """
    Rule-based risk evaluation layer.

    This is NOT a scientifically perfect model — it uses deterministic rules.
    """

    def assess(
        self,
        action: ActionRequest,
        policy_violations: int = 0,
        historical_reliability: float = 95.0,
    ) -> RiskAssessment:
        factors: dict[str, float] = {}
        reasons: list[str] = []

        # Action type sensitivity
        action_sensitivity = ACTION_SENSITIVITY.get(action.action, DEFAULT_SENSITIVITY)
        factors["action_sensitivity"] = action_sensitivity
        if action_sensitivity >= 70:
            reasons.append(f"High-sensitivity action: {action.action}")

        # Financial value
        amount = self._extract_amount(action)
        financial_risk = 0.0
        if amount > 0:
            if amount > 100000:
                financial_risk = 90
                reasons.append(f"Large financial value: {amount:,.0f}")
            elif amount > 50000:
                financial_risk = 70
                reasons.append(f"Significant financial value: {amount:,.0f}")
            elif amount > 10000:
                financial_risk = 50
                reasons.append(f"Moderate financial value: {amount:,.0f}")
            else:
                financial_risk = 20
        factors["financial_value"] = financial_risk

        # Target risk
        target_risk = 30.0 if action.target else 10.0
        factors["target"] = target_risk

        # Permission scope
        perm_count = len(action.requested_permissions)
        perm_risk = min(perm_count * 15, 60)
        factors["permission_scope"] = perm_risk
        if perm_count > 2:
            reasons.append(f"Multiple permissions requested: {perm_count}")

        # Policy violations history
        violation_risk = min(policy_violations * 20, 80)
        factors["policy_violations"] = violation_risk
        if policy_violations > 0:
            reasons.append(f"Historical policy violations: {policy_violations}")

        # Historical reliability (inverse — lower reliability = higher risk)
        reliability_risk = max(0, 100 - historical_reliability)
        factors["reliability"] = reliability_risk

        # Weighted score
        weights = {
            "action_sensitivity": 0.3,
            "financial_value": 0.25,
            "target": 0.1,
            "permission_scope": 0.1,
            "policy_violations": 0.15,
            "reliability": 0.1,
        }
        risk_score = sum(factors[k] * weights[k] for k in weights)
        risk_score = round(min(max(risk_score, 0), 100), 1)

        risk_level = self._score_to_level(risk_score)
        recommended = self._recommend_decision(risk_score, risk_level)

        if not reasons:
            reasons.append("Standard risk profile")

        return RiskAssessment(
            risk_score=risk_score,
            risk_level=risk_level,
            reasons=reasons,
            recommended_decision=recommended,
            factors=factors,
        )

    def _extract_amount(self, action: ActionRequest) -> float:
        for key in ("amount", "value", "total", "price"):
            val = action.parameters.get(key)
            if val is not None:
                try:
                    return float(str(val).replace(",", "").replace("₹", "").replace("$", ""))
                except (ValueError, TypeError):
                    pass
        return 0.0

    def _score_to_level(self, score: float) -> RiskLevel:
        if score >= 75:
            return RiskLevel.CRITICAL
        if score >= 55:
            return RiskLevel.HIGH
        if score >= 30:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _recommend_decision(self, score: float, level: RiskLevel) -> str:
        if level == RiskLevel.CRITICAL:
            return "deny"
        if level == RiskLevel.HIGH:
            return "require_approval"
        if level == RiskLevel.MEDIUM:
            return "require_approval"
        return "allow"
