"""First action: authenticate, submit a safe demo email, inspect audit.

Requires a running API in demo mode:

    python -m uvicorn apps.api.main:app --port 8000

Run from the repository root:

    python examples/basic_action.py
"""

from __future__ import annotations

from packages.sdk.openworld import OpenWorldClient
from packages.sdk.openworld.exceptions import AuthError, ForbiddenError


def main() -> None:
    with OpenWorldClient(base_url="http://localhost:8000", timeout=30.0) as client:
        health = client.health()
        print(f"health={health.status} demo_mode={health.demo_mode}")

        client.authenticate("agent-email-bot")
        submitted = client.actions.submit(
            agent="EmailBot",
            action="email.send",
            parameters={"to": "dev@example.com", "subject": "OpenWorld onboarding"},
            auto_approve=True,
            idempotency_key="onboarding-basic-action",
        )
        action = submitted.action
        print(f"action_id={action['id']} status={action['status']}")

        status = client.actions.status(action["id"])
        print(f"status_check={status.action['status']}")

        operator = client.get_demo_token("agent-ops-bot")
        events = client.audit.list(token=operator, limit=5, subject=action["id"])
        print(f"audit_events={events.total}")


if __name__ == "__main__":
    try:
        main()
    except AuthError as exc:
        raise SystemExit(f"auth failed: {exc.message} request_id={exc.request_id}") from exc
    except ForbiddenError as exc:
        raise SystemExit(f"forbidden: {exc.message} request_id={exc.request_id}") from exc
