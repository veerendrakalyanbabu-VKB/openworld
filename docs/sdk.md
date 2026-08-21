# SDK Guide

## Installation

```bash
pip install -e .
```

## Usage

```python
from openworld import OpenWorldClient

client = OpenWorldClient(base_url="http://localhost:8000")

# Health check
client.health()

# List agents
agents = client.agents.list()

# Request an action
result = client.actions.request(
    agent="FinanceBot",
    action="payment.create",
    parameters={"amount": 5000, "recipient": "Vendor"},
)

# Simulate without executing
sim = client.actions.simulate(
    agent="FinanceBot",
    action="payment.create",
    parameters={"amount": 48500},
)

# Approve pending action
client.approvals.approve(action_id="...")

# Query audit log
events = client.audit.list(limit=20)
```

## CLI

```bash
openworld health
openworld agents list
openworld actions list
openworld policies list
openworld audit list
openworld demo
```
