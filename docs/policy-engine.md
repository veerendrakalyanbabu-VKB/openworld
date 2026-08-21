# Policy Engine

## Overview

The OpenWorld policy engine is a **deterministic** rule evaluation system. It does not use LLMs to make security decisions.

## Rule Structure

```
WHEN
  Agent: FinanceBot
  Action: payment.*
  Condition: amount > 50000
THEN
  REQUIRE HUMAN APPROVAL
```

## Supported Operators

| Operator | Description |
|----------|-------------|
| eq | Equal |
| ne | Not equal |
| gt | Greater than |
| gte | Greater than or equal |
| lt | Less than |
| lte | Less than or equal |
| contains | String contains |
| matches | Regex match |

## Effect Precedence

1. **DENY** — highest priority, blocks the action
2. **REQUIRE_APPROVAL** — queues for human review
3. **ALLOW** — permits execution

Rules are sorted by priority (lower number = higher priority).

## Field Resolution

Conditions can reference:
- `parameters.<key>` — action parameters
- `context.<key>` — action context
- `agent`, `agent_id`, `action`, `target` — direct fields

## Simulation

The engine supports dry-run simulation via `PolicyEngine.simulate()` without side effects.
