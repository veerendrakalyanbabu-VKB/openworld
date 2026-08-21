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

### Prerequisites

- Python 3.11+
- Node.js 20+ (for frontend)
- pip

### Backend

```bash
pip install -e ".[dev]"
uvicorn apps.api.main:app --reload --port 8000
```

API docs: http://localhost:8000/api/docs

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

UI: http://localhost:3000

### Docker

```bash
docker compose up
```

### CLI

```bash
openworld health
openworld agents list
openworld actions list
openworld policies list
openworld audit list
openworld demo
```

### SDK

```python
from openworld import OpenWorldClient

client = OpenWorldClient()

result = client.actions.request(
    agent="invoice-bot",
    action="invoice.send",
    parameters={"invoice_id": "INV-1001"},
)
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

- [Architecture](docs/architecture.md)
- [Policy Engine](docs/policy-engine.md)
- [Trust Model](docs/trust-model.md)
- [API Reference](docs/api.md)
- [SDK Guide](docs/sdk.md)
- [Development](docs/development.md)
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
- [ ] Redis caching
- [ ] Real connector integrations
- [ ] Multi-tenant SaaS

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT License — see [LICENSE](LICENSE).

---

**Human Intent. Machine Execution. Verifiable Results.**
