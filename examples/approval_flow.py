"""Approval flow: FinanceBot payment requires operator approval.

Requires a running API in demo mode on http://localhost:8000
"""

from __future__ import annotations

from packages.sdk.openworld import OpenWorldClient


def main() -> None:
    with OpenWorldClient(base_url="http://localhost:8000") as client:
        finance = client.get_demo_token("agent-finance-bot")
        pending = client.actions.submit(
            agent="FinanceBot",
            action="payment.create",
            parameters={"amount": 75000, "recipient": "Onboarding Vendor"},
            token=finance,
        )
        action_id = pending.action["id"]
        print(f"pending={action_id} status={pending.action['status']}")

        operator = client.get_demo_token("agent-ops-bot")
        approved = client.approvals.approve(action_id, token=operator)
        print(f"approved status={approved.action['status']}")


if __name__ == "__main__":
    main()
