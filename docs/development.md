# Development Guide

## Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 16+ (recommended for Milestone 1.3A persistence)

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env
```

### PostgreSQL (persistence)

**Option A — Docker:**

```bash
docker compose up -d postgres
export OPENWORLD_DATABASE_URL=postgresql://openworld:openworld@localhost:5432/openworld
```

**Option B — Local install (Windows):**

```bash
winget install PostgreSQL.PostgreSQL.17
# Create role/database once as postgres superuser (use your own dev password)
# CREATE ROLE openworld WITH LOGIN PASSWORD 'your-local-dev-password';
# CREATE DATABASE openworld OWNER openworld;

cp .env.example .env
# OPENWORLD_DATABASE_URL=postgresql://openworld:<password>@localhost:5432/openworld
alembic upgrade head
uvicorn apps.api.main:app --reload --port 8000
python scripts/postgres_restart_proof.py
```

SQLite works for quick local runs (`OPENWORLD_DATABASE_URL=sqlite:///./openworld.db`).

### Migrations

```bash
alembic upgrade head          # apply schema
alembic revision --autogenerate -m "description"  # new migration
```

Schema is applied automatically on API startup via Alembic.

### Demo seed

On startup the API loads deterministic demo agents/policies (`core/demo/seed.py`). Demo actions are seeded once when the database is empty. All demo data is labeled `DEMO MODE — SYNTHETIC DATA`.

Set `OPENWORLD_SECRET_KEY` to at least 32 characters (HS256 requirement). The default in `apps/api/config.py` is a dev-only placeholder.

### Authentication (JWT)

`POST /api/v1/actions` and `/simulate` require `Authorization: Bearer <token>`. Identity comes from the JWT — not the request body.

Demo tokens: `GET /api/v1/auth/demo-agents` or `POST /api/v1/auth/token` (demo mode only).

### Authorization (Milestone 2.0A)

Roles are stored in agent `metadata.roles` and resolved server-side (never from request body):

| Role | Purpose |
|------|---------|
| `agent` | Submit actions / simulate |
| `operator` | List, approve, and deny pending approvals; read audit |
| `policy_admin` | Create/update policies |
| `system_admin` | Inherits operator + policy_admin |

Demo agents with elevated roles: **OpsBot** (`agent-ops-bot`, operator), **ApiBot** (`agent-api-bot`, policy_admin).

| Endpoint | Auth |
|----------|------|
| `GET /health`, `/stats`, `/agents`, `/actions`, `/policies` | Public read |
| `POST /actions`, `/simulate` | JWT (agent) |
| `GET/POST /approvals/*` | JWT + operator (or system_admin) |
| `POST /policies` | JWT + policy_admin (or system_admin) |
| `GET /audit` | JWT (production: agents scoped to own subject) |
| `POST /audit` | Not allowed (405) |

Approval approver identity is always the authenticated operator's agent ID — body `approver` is ignored.

### Production vs demo

| Setting | Demo (`OPENWORLD_DEMO_MODE=true`) | Production (`false`) |
|---------|-----------------------------------|----------------------|
| Database | SQLite OK | PostgreSQL required |
| Secret | Dev placeholder OK | Custom `OPENWORLD_SECRET_KEY` (≥32 bytes) |
| Policy default | Allow unmatched (simulation) | Default-deny |
| Approvals / audit | JWT + roles | JWT + roles |
| Startup | Labeled demo mode | `validate_production_safety()` on boot |

Set `OPENWORLD_SECRET_KEY` to at least 32 characters (HS256 requirement). Never commit `.env` — use `.env.example` placeholders only.

### Role administration (Milestone 2.0B)

Only `SYSTEM_ADMIN` may mutate roles via:

- `GET /api/v1/agents/{agent_id}/roles`
- `POST /api/v1/agents/{agent_id}/roles` body: `{"role": "operator"|"policy_admin"|"system_admin"}`
- `DELETE /api/v1/agents/{agent_id}/roles/{role}`

Demo **AdminBot** (`agent-admin-bot`) has `system_admin`. Role changes emit `role_assigned` / `role_revoked` audit events. The final system admin cannot be removed.

### Policy lifecycle (Milestone 2.0B)

`POLICY_ADMIN` / `SYSTEM_ADMIN` may:

- `PUT /api/v1/policies/{id}` — update with version bump + snapshot
- `POST /api/v1/policies/{id}/disable|enable`
- `GET /api/v1/policies/{id}/versions` — historical snapshots

### Audit export

- `GET /api/v1/audit/export?format=json|csv&limit=500` — same authorization scoping as audit read; max 1000 rows; export is audited.

### Identity abstraction

Authentication flows through `IdentityProvider` → `AuthenticatedPrincipal` → role resolution. Current implementation: `JwtIdentityProvider` (HS256 JWT).

### Idempotency

Pass `Idempotency-Key` header on `POST /api/v1/actions`. Same key + same payload returns cached response; conflicting payload → 409.

## Running Tests

```bash
python -m pytest tests/ -q     # uses in-memory SQLite (no Postgres required)
ruff check .
python scripts/smoke_test_api.py   # requires API on :8000
```

### Restart persistence verification

`tests/test_db_repositories.py::test_restart_persistence_simulation` clears in-memory caches and reloads from the database — proving agents, actions, approvals, verifications, and audit survive a simulated restart.

For live PostgreSQL verification: `python scripts/postgres_restart_proof.py` (requires PostgreSQL on :5432).

## Frontend

Use **one** dev server only:

```bash
cd apps/web && npm run dev
```

Do not run `npm run build` while `npm run dev` is active. If `.next` cache corrupts:

1. Stop all Next.js processes
2. Delete `apps/web/.next`
3. Start one fresh `npm run dev`

## Project Structure

- `core/` — Domain logic and Trust Core engines
- `core/db/` — SQLAlchemy models, repositories, mappers
- `apps/api/` — FastAPI application
- `alembic/` — Database migrations
- `tests/` — Test suite
