# OPENWORLD

## The Trust Layer for the Agentic Internet.

> **Human Intent. Machine Execution. Verifiable Results.**

OpenWorld is an open, secure, developer-first infrastructure layer that allows AI agents to interact with software, APIs, services, and digital workflows under explicit permissions, policies, verification, and auditability.

This is **not** a chatbot. This is **not** an AI wrapper. This is the trust infrastructure for the agentic internet.

---

## The Problem

AI agents are increasingly executing real actions — sending emails, processing payments, modifying data. But there's no standard way to:

- Verify agent identity
- Enforce permissions deterministically
- Require human approval for sensitive actions
- Verify that actions actually succeeded
- Maintain an auditable trail of everything

## The Solution

OpenWorld provides a complete trust pipeline:

```
AI AGENT → IDENTITY → PERMISSION → POLICY → RISK → APPROVAL → EXECUTE → VERIFY → AUDIT
```

Every decision is **deterministic**. The policy engine — not an LLM — decides permissions. Every action is verified. Every event is audited.

## Architecture

```
openworld/
├── apps/
│   ├── web/          # Next.js command center UI
│   └── api/          # FastAPI backend
├── core/
│   ├── policies/     # Deterministic policy engine
│   ├── risk/         # Rule-based risk evaluation
│   ├── execution/    # Registered action executors
│   ├── verification/ # Outcome verification
│   └── audit/        # Immutable audit logging
├── packages/
│   └── sdk/          # Python SDK + CLI
└── tests/
```

## Quick Start

Full walkthrough: [Developer Onboarding](docs/onboarding.md). Gateway: [docs/gateway.md](docs/gateway.md). SDK: [docs/sdk.md](docs/sdk.md).

### Prerequisites

- Python 3.11+
- Node.js 20+ (frontend)
- PostgreSQL 17 recommended (SQLite OK for a first boot)

### Backend (PowerShell)

```powershell
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
python -m alembic upgrade head
python -m uvicorn apps.api.main:app --port 8000
```

### Backend (Linux / macOS)

```bash
python -m pip install -e ".[dev]"
cp .env.example .env
python -m alembic upgrade head
python -m uvicorn apps.api.main:app --port 8000
```

API: http://localhost:8000/api/docs — health: `/api/v1/health` — ready: `/api/v1/ready`

### Frontend

```powershell
cd apps\web
npm install
npm run dev
```

```bash
cd apps/web && npm install && npm run dev
```

UI: http://localhost:3000

### Docker (local stack)

```bash
docker compose up
```

Compose starts PostgreSQL, API, and web. Do not put secrets in images.

### SDK (real client)

```python
from packages.sdk.openworld import OpenWorldClient

with OpenWorldClient(base_url="http://localhost:8000") as client:
    client.authenticate("agent-email-bot")
    result = client.actions.submit(
        agent="EmailBot",
        action="email.send",
        parameters={"to": "dev@example.com", "subject": "Hello"},
        auto_approve=True,
        idempotency_key="quickstart-email-1",
    )
    print(result.action["status"])
```

Run `python examples/basic_action.py` with the API up. Identity is the JWT, never a body `agent_id`.

### CLI

```powershell
openworld health
openworld agents list
openworld demo
```

### Tests

```powershell
python -m pytest tests/ -q
python -m ruff check .
python scripts/smoke_test_api.py
```

## Milestone 2.0B — Governance + Production Identity Hardening

- SYSTEM_ADMIN role administration (`GET/POST/DELETE /agents/{id}/roles`)
- Policy lifecycle with versioning (`PUT`, enable/disable, version history)
- Intelligence endpoint authorization (production requires JWT; role-scoped queries)
- Authorized audit export (JSON/CSV, bounded, auditable)
- Identity provider abstraction (`IdentityProvider` / `JwtIdentityProvider`)
- Timezone-aware UTC datetimes (`core.utils.time.utc_now`)

See [Architecture](docs/architecture.md) for governance details.

## Milestone 2.0A — Production Hardening + Authorization

- Role-based authorization: `AGENT`, `OPERATOR`, `POLICY_ADMIN`, `SYSTEM_ADMIN`
- JWT required for approvals, audit read, policy mutation, and action submission
- Production mode enforces PostgreSQL, strong secrets, default-deny, authenticated approvals
- Demo mode retains synthetic data and executors (clearly labeled)

See [Development Guide](docs/development.md) for configuration and the authorization matrix in [Architecture](docs/architecture.md).

## Milestone 1.3A — PostgreSQL Persistence

- SQLAlchemy + Alembic migrations
- Repository layer for agents, policies, actions, audit
- State survives API restart
- Docker Compose PostgreSQL service

See [Development Guide](docs/development.md) for database setup. Live PostgreSQL restart gate: `python scripts/postgres_restart_proof.py`.

## Security Model

- **Deterministic policy engine** — LLMs recommend, policies decide
- **Role-based authorization** — operators approve, policy admins mutate policies
- **Explicit executor registration** — no arbitrary shell execution
- **Verification before trust** — actions aren't "successful" until verified
- **Immutable audit trail** — every decision is recorded
- **Human approval** — sensitive actions require explicit approval
- **Explainable trust scores** — no arbitrary AI-generated numbers

See [SECURITY.md](SECURITY.md) for responsible disclosure.

## Testing

```bash
pytest tests/ -v
ruff check core/ apps/ packages/ tests/
```

## Documentation

- [Developer Onboarding](docs/onboarding.md)
- [Architecture](docs/architecture.md)
- [API Gateway](docs/gateway.md)
- [Policy Engine](docs/policy-engine.md)
- [Trust Model](docs/trust-model.md)
- [API Reference](docs/api.md)
- [SDK Guide](docs/sdk.md)
- [Development](docs/development.md)
- [Deployment](docs/deployment.md) (READY FOR DEPLOYMENT, not actually deployed)
- [External beta](docs/beta.md) (BETA-READY, not beta-live)
- [Roadmap](docs/roadmap.md)

## Roadmap

- [x] Core domain models
- [x] Deterministic policy engine
- [x] Risk evaluation
- [x] Action lifecycle (request → verify → audit)
- [x] Human approval workflow
- [x] Command center UI
- [x] Python SDK + CLI
- [x] Demo mode with synthetic data
- [x] PostgreSQL/SQLite persistence (Milestone 1.3 — live PostgreSQL restart verified)
- [x] JWT agent authentication
- [x] Durable idempotency
- [x] Production authorization boundaries (Milestone 2.0A)
- [x] Governance: roles, policy lifecycle, audit export (Milestone 2.0B)
- [x] SDK + API gateway (Milestone 2.1)
- [x] Bounded GitHub issue connector, disabled by default (Milestone 2.2)
- [ ] Cloud deployment
- [ ] External beta
- [ ] Monetization foundation

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT License — see [LICENSE](LICENSE).

---

**Human Intent. Machine Execution. Verifiable Results.**
