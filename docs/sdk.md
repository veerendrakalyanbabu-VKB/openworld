# SDK Guide

## Installation

```bash
pip install -e .
```

## Usage

```python
from openworld import AgentGateway

with AgentGateway(agent="EmailBot", policy="policy-email-limits", auto_approve=True) as gateway:
    result = gateway.execute(
        action="send_email",
        recipient="customer@example.com",
        purpose="invoice_delivery",
    )
    print(result.action["status"])
```

Lower-level client:

```python
from packages.sdk.openworld import OpenWorldClient
from packages.sdk.openworld.exceptions import AuthError, ForbiddenError, ConflictError

client = OpenWorldClient(base_url="http://localhost:8000")

# Health and readiness
client.health()
client.readiness()
client.stats()

# Authentication (demo mode). Identity is always the bearer token, never a body field.
token = client.get_demo_token("agent-email-bot")
client.set_token(token)
# or: client.authenticate("agent-email-bot")
# Privileged calls (approvals, audit, policy/role admin) require an explicit token.

Examples in `examples/`: `basic_action.py`, `approval_flow.py`, `audit_query.py`.

# Correlation ID for distributed tracing
client.set_correlation_id("my-trace-id")

# List agents
agents = client.agents.list()

# Submit an action (with idempotency key)
result = client.actions.submit(
    agent="FinanceBot",
    action="payment.create",
    parameters={"amount": 5000, "recipient": "Vendor"},
    idempotency_key="unique-key-123",
)

# Simulate without executing
sim = client.actions.simulate(
    agent="FinanceBot",
    action="payment.create",
    parameters={"amount": 48500},
)

# Check action status
status = client.actions.status(action_id="...")

# Approve pending action (requires operator role)
client.approvals.approve(action_id="...")

# Policy admin
client.policies.create("policy-id", "My Policy", token=admin_token)

# Role admin
client.roles.assign("agent-id", "operator", admin_token=admin_token)

# Query and export audit log
events = client.audit.list(limit=20)
export = client.audit.export(format="json", limit=100)
```

## Error Handling

The SDK raises typed exceptions mapped from HTTP status codes:

| Exception       | HTTP Status |
|-----------------|-------------|
| `AuthError`     | 401         |
| `ForbiddenError`| 403         |
| `NotFoundError` | 404         |
| `ConflictError` | 409         |
| `TimeoutError`  | (timeout)   |

```python
try:
    client.approvals.list()
except AuthError as e:
    print(e.message, e.request_id)
```

The SDK does not evaluate policy, risk, or approvals. Those decisions stay on the API.

## CLI

```bash
openworld health
openworld agents list
openworld actions list
openworld policies list
openworld audit list
openworld demo
```
