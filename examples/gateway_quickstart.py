"""Gateway quickstart: one action through identity, policy, risk, execution, verification.

Requires a running API in demo mode:

    python -m uvicorn apps.api.main:app --port 8000

Run from the repository root:

    python examples/gateway_quickstart.py
"""

from __future__ import annotations

import sys
import uuid

from packages.sdk.openworld import AgentGateway, OpenWorldClient

QUICKSTART_AGENT = "EmailBot"
QUICKSTART_AGENT_ID = "agent-email-bot"
QUICKSTART_CAPABILITY = "email.send"
QUICKSTART_POLICY_ID = "policy-email-limits"


def ensure_demo_prerequisites(client: OpenWorldClient) -> None:
    """Verify the demo agent, capability, and policy the quickstart legitimately needs."""
    health = client.health()
    if not health.demo_mode:
        raise SystemExit(
            "Quickstart requires OPENWORLD_DEMO_MODE=true. "
            "Production default-deny is unchanged; use demo mode for this walkthrough."
        )

    agents = client.agents.list().agents
    email_bot = next((a for a in agents if a.name == QUICKSTART_AGENT or a.id == QUICKSTART_AGENT_ID), None)
    if not email_bot:
        raise SystemExit(
            f"Demo agent {QUICKSTART_AGENT!r} not found. "
            "Start the API so demo seed loads (alembic upgrade head, then uvicorn)."
        )
    if QUICKSTART_CAPABILITY not in email_bot.capabilities:
        raise SystemExit(
            f"{QUICKSTART_AGENT} must include capability {QUICKSTART_CAPABILITY!r}. "
            f"Found: {email_bot.capabilities}"
        )

    policies = client.policies.list().policies
    policy = next((p for p in policies if p.get("id") == QUICKSTART_POLICY_ID), None)
    if not policy:
        raise SystemExit(
            f"Demo policy {QUICKSTART_POLICY_ID!r} not found. "
            "Ensure demo seed policies are loaded."
        )
    if not policy.get("enabled", True):
        raise SystemExit(f"Demo policy {QUICKSTART_POLICY_ID!r} must be enabled.")


def _stage_names(action: dict) -> list[str]:
    return [stage["stage"] for stage in action.get("stages", [])]


def main() -> None:
    with OpenWorldClient(base_url="http://localhost:8000", timeout=30.0) as client:
        ensure_demo_prerequisites(client)

    with AgentGateway(
        agent=QUICKSTART_AGENT,
        policy=QUICKSTART_POLICY_ID,
        auto_approve=True,
    ) as gateway:
        result = gateway.execute(
            action="send_email",
            recipient="customer@example.com",
            purpose="invoice_delivery",
            subject="OpenWorld Gateway MVP",
            idempotency_key=f"gateway-quickstart-email-{uuid.uuid4()}",
        )

    action = result.action
    canonical_action = action.get("action")
    status = action.get("status")
    risk = action.get("risk_level")
    stages = _stage_names(action)

    stages_by_name = {s["stage"]: s for s in action.get("stages", [])}
    policy_stage = stages_by_name.get("policy", {})
    policy_decision = action.get("policy_decision") or {}
    policy_outcome = (policy_decision.get("decision") or policy_stage.get("status") or "unknown").upper()

    print(f"action={canonical_action} status={status} risk={risk}")
    print(f"pipeline={' -> '.join(stages)}")
    print(f"policy={policy_outcome} ({QUICKSTART_POLICY_ID})")
    print("execution=sandbox (DEMO DATA)")
    print(f"verification={status.upper() if status == 'verified' else status}")
    print("audit=recorded")
    print("sandbox=DEMO DATA (mock email executor, not a live mailbox)")

    if status != "verified":
        print("Quickstart failed: expected verified after full Trust Pipeline.", file=sys.stderr)
        if action.get("policy_decision"):
            print(f"policy_decision={action['policy_decision']}", file=sys.stderr)
        for stage in action.get("stages", []):
            if stage.get("status") in {"denied", "failed", "blocked", "capability_denied"}:
                print(f"blocked_at={stage}", file=sys.stderr)
        raise SystemExit(1)

    required = {"identity", "capability", "policy", "risk", "execution", "verification"}
    missing = required - set(stages)
    if missing:
        print(f"Quickstart incomplete: missing stages {sorted(missing)}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
