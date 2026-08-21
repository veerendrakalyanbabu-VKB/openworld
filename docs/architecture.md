# Architecture

## Overview

OpenWorld is a modular monolith:

1. **Core** — Domain models and Trust Core engines
2. **Apps** — FastAPI backend + Next.js frontend
3. **Packages** — SDK and utilities

## Trust Pipeline

```
Agent Request (POST /api/v1/actions)
    ↓
Identity → Capability → Policy → Risk → Decision
    ↓
Approval (when required)
    ↓
Execution → Verification → Audit
```

**DECISION ≠ EXECUTION** — blocked actions never reach the execution engine.

## Persistence

Trust Core state survives API restart via PostgreSQL (SQLite for local dev).

| Layer | Role |
|-------|------|
| `core/models/` | Pydantic domain models (business logic) |
| `core/db/models.py` | SQLAlchemy ORM rows |
| `core/db/mappers.py` | ORM ↔ domain conversion |
| `core/db/repositories.py` | Data access (no business rules) |
| `alembic/` | Schema migrations |

### Tables

| Table | Persists |
|-------|----------|
| `agents` | Agent identity, capabilities, trust dimensions |
| `policies` | Policy rules (JSON) |
| `actions` | Full action lifecycle + approval fields + verification_id |
| `audit_events` | Append-only audit evidence |
| `idempotency_records` | Durable idempotency keys (unique per agent) |

Approvals are stored as fields on `actions` (`approval_status`, `approval_actor`, etc.). Verifications are stored via `verification_id` and stage records on actions.

## Authentication & Authorization

JWT bearer tokens authenticate API access. Claims: `sub` (agent ID), `iss`, `aud`, `exp`. Secret: `OPENWORLD_SECRET_KEY` from environment only.

Roles live in persisted agent `metadata.roles` and are resolved server-side:

| Role | Capabilities |
|------|--------------|
| `agent` | `POST /actions`, `/simulate` |
| `operator` | Approval queue read/approve/deny; audit read |
| `policy_admin` | `POST /policies` |
| `system_admin` | operator + policy_admin |

### Authorization matrix

| Resource | GET | POST / mutate |
|----------|-----|---------------|
| Health / stats | Public | — |
| Agents / actions | Public read | Actions: JWT agent |
| Policies | Public read | POST: policy_admin |
| Approvals | operator JWT | approve/deny: operator JWT |
| Audit | JWT (scoped in prod) | No client writes (405) |
| Simulate | — | JWT agent |

Identity for action submission and approvals always comes from the JWT `sub` claim — never from request body fields.

### Governance (Milestone 2.0B)

| Capability | Endpoint | Role |
|------------|----------|------|
| Role list | `GET /agents/{id}/roles` | self or SYSTEM_ADMIN |
| Role assign/revoke | `POST/DELETE /agents/{id}/roles` | SYSTEM_ADMIN |
| Policy update | `PUT /policies/{id}` | POLICY_ADMIN |
| Policy enable/disable | `POST /policies/{id}/enable\|disable` | POLICY_ADMIN |
| Policy history | `GET /policies/{id}/versions` | public read |
| Audit export | `GET /audit/export` | same as audit read |
| Intelligence | `GET /intelligence/query` | production: JWT + role scope |

Role and policy mutations emit backend audit events (`role_assigned`, `role_revoked`, `policy_created`, `policy_updated`, `policy_disabled`, `policy_enabled`, `audit_exported`).

## Idempotency

`Idempotency-Key` header on action creation. Unique constraint on `(agent_id, idempotency_key)` prevents duplicate execution across restarts.

## Policy Default-Deny & Production Safety

Production (`OPENWORLD_DEMO_MODE=false`): unmatched policies → DENY; PostgreSQL required; custom secret required; `validate_production_safety()` runs at startup. Demo mode preserves allow-unmatched for simulation and labels responses `demo_mode: true`.

## AppState

`AppState` uses write-through caches backed by repositories. On startup:

1. Alembic migration to latest schema
2. Demo seed (agents, policies)
3. Restore pending approvals from database

## API Design

Versioned REST at `/api/v1/`. Audit events are append-only — no client edit/delete endpoints.

## Frontend

Next.js App Router consuming real backend data. No hardcoded trust decisions.
