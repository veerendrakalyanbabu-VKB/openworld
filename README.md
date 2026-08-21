# OPENWORLD

## The Trust Layer for the Agentic Internet

> **Human Intent. Machine Execution. Verifiable Results.**

**OpenWorld Gateway v0.1.0 — Early Developer Preview**

OpenWorld is open, developer-first infrastructure that lets AI agents act on software, APIs, and workflows under explicit **identity**, **capabilities**, **policy**, **risk**, **approval**, **execution**, **verification**, and **audit**.

**Core principle: Never trust the agent. Verify the action.**

### Release status

- **Repository:** Publicly available on GitHub as source code.
- **Run locally:** Clone the repo, install dependencies, and start the API and web UI on your machine.
- **Hosted deployment:** No public hosted OpenWorld instance is available yet. There is no live production URL for this release.
- **Integrations:** Sandbox and demo executors (email, payments, webhooks, etc.) are **not** live production integrations.

This release is an **Early Developer Preview**. It is **not** enterprise production-ready, **not** a live cloud deployment, and **not** backed by real customer integrations. Demo executors are sandbox/mock and labeled **DEMO DATA**.

---

## Trust Pipeline

Every action passes through a deterministic trust pipeline. The policy engine — not an LLM — decides authorization.

```
REQUESTED
  → IDENTITY        (JWT agent identity)
  → CAPABILITY      (explicit agent capability grant)
  → POLICY          (deterministic allow/deny)
  → RISK            (rule-based score + factors)
  → DECISION        (pipeline outcome)
  → APPROVAL        (human gate when required)
  → EXECUTION       (registered executor only)
  → VERIFICATION    (outcome checked separately)
  → AUDIT           (immutable lifecycle record)
```

| Stage | What it enforces |
|-------|------------------|
| **Identity** | Bearer JWT maps to a registered agent |
| **Capabilities** | Agent must hold an explicit catalog capability (wildcards rejected) |
| **Policy** | Deterministic rules match agent, action, and conditions |
| **Risk** | Explainable factors (recipient, data sensitivity, financial impact) |
| **Decision** | Pipeline outcome before execution |
| **Approval** | Operators approve or deny sensitive actions |
| **Execution** | Only registered executors; direct bypass is rejected |
| **Verification** | `EXECUTED` ≠ `VERIFIED`; failures are distinct |
| **Audit** | Every gate and outcome is recorded |

---

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────────────┐
│ Agent / SDK │────▶│ FastAPI Gateway  │────▶│ Trust Core (core/)          │
│  (JWT)      │     │ apps/api/        │     │ policy · risk · lifecycle   │
└─────────────┘     └────────┬─────────┘     │ execution · verification    │
                             │               │ audit                       │
┌─────────────┐              │               └──────────────┬──────────────┘
│ Next.js UI  │──────────────┘                              │
│ apps/web/   │                                             ▼
└─────────────┘                                    PostgreSQL / SQLite
```

```
openworld/
├── apps/
│   ├── web/          # Next.js command center UI
│   └── api/          # FastAPI gateway + routers
├── core/
│   ├── policies/     # Deterministic policy engine
│   ├── risk/         # Rule-based risk evaluation
│   ├── execution/    # Registered action executors (sandbox in demo)
│   ├── verification/ # Outcome verification
│   └── audit/        # Immutable audit logging
├── packages/sdk/     # Python SDK + CLI
├── openworld/        # Public import: from openworld import AgentGateway
├── examples/         # Quickstart scripts
├── docs/             # Architecture, deployment, SDK guides
└── tests/            # 192+ automated tests
```

---

## Quick Start

Full walkthrough: [Developer Onboarding](docs/onboarding.md) · [Gateway](docs/gateway.md) · [SDK](docs/sdk.md)

### Prerequisites

- Python 3.11+
- Node.js 20+ (frontend)
- PostgreSQL 17 recommended (SQLite OK for first boot)

### Local development

Install dependencies and apply migrations from the repository root:

**PowerShell**

```powershell
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
python -m alembic upgrade head
```

**Linux / macOS**

```bash
python -m pip install -e ".[dev]"
cp .env.example .env
python -m alembic upgrade head
```

Start the API:

```powershell
python -m uvicorn apps.api.main:app --port 8000
```

**LOCAL DEVELOPMENT URLs** (not publicly hosted):

API documentation:

```text
http://localhost:8000/api/docs
```

Health:

```text
http://localhost:8000/api/v1/health
```

Readiness:

```text
http://localhost:8000/api/v1/ready
```

Start the web UI:

```powershell
cd apps\web
npm install
npm run dev
```

Local web UI (**LOCAL DEVELOPMENT URL**):

```text
http://localhost:3000
```

### Run the gateway quickstart

With the API running in **demo mode** (default):

```powershell
python examples/gateway_quickstart.py
```

**Expected output (sandbox — not a live mailbox):**

```
action=email.send status=verified risk=low
pipeline=requested -> identity -> capability -> policy -> risk -> decision -> execution -> verification -> complete
policy=ALLOW (policy-email-limits)
execution=sandbox (DEMO DATA)
verification=VERIFIED
audit=recorded
sandbox=DEMO DATA (mock email executor, not a live mailbox)
```

Restart the API after pulling code changes — a stale process can serve old pipeline behavior.

### Docker (local stack)

```bash
docker compose up
```

Compose starts PostgreSQL, API, and web. Do not put secrets in images.

---

## SDK Example

```python
from openworld import AgentGateway

with AgentGateway(
    agent="EmailBot",
    policy="policy-email-limits",
    auto_approve=True,
) as gateway:
    result = gateway.execute(
        action="send_email",
        recipient="customer@example.com",
        purpose="invoice_delivery",
    )
    print(result.action["status"])  # verified (sandbox)
```

Lower-level client (same gateway, more endpoints):

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

Identity is always the JWT bearer token — never a trusted body `agent_id`. See `examples/basic_action.py`, `examples/approval_flow.py`, and `examples/audit_query.py`.

### CLI

```powershell
openworld health
openworld agents list
openworld demo
```

---

## What's in v0.1.0

**Implemented**

- Full trust pipeline with execution bypass protection
- FastAPI gateway + Next.js command center (action detail pipeline view)
- JWT roles: `viewer`, `agent`, `operator`, `policy_admin`, `system_admin`
- Agent create/update with capability catalog (wildcards rejected)
- Python SDK: `AgentGateway` + `OpenWorldClient` + CLI
- Demo/sandbox executors (email, webhook, API, payment, invoice; optional GitHub connector disabled by default)
- PostgreSQL/SQLite persistence, Alembic migrations, Docker artifacts, CI

**Simulated / demo only**

- Email, payment, and webhook executors (mock responses, labeled DEMO DATA)
- Demo JWT token issuance (`OPENWORLD_DEMO_MODE=true`)

**Planned — not in this release**

- Hosted cloud deployment · external beta · live payments · enterprise SSO · agent marketplace

See [Roadmap](docs/roadmap.md).

---

## Security Model

- **Default deny** in production (`OPENWORLD_DEMO_MODE=false`); demo mode uses labeled synthetic data
- **Server-side authorization** on mutations (roles enforced on API)
- **Explicit capabilities** — unrestricted wildcards rejected
- **Execution boundary** — `ExecutionEngine.execute` requires `pipeline_authorized=True`
- **Verification separate from execution** — actions are not trusted until verified
- **Immutable audit trail** — lifecycle events recorded at each gate
- **No arbitrary shell/SQL/code execution** — only registered executors
- **Secrets via environment variables** — never committed to source

Production startup requires PostgreSQL, a non-default `OPENWORLD_SECRET_KEY` (≥32 chars), and `OPENWORLD_DEMO_MODE=false`. See [SECURITY.md](SECURITY.md) and [Deployment](docs/deployment.md).

---

## Testing

```powershell
python -m pytest tests/ -q
python -m ruff check .
cd apps\web
npm run lint
npm run build
```

Current suite: **192 tests passing** (trust pipeline, gateway, SDK, authorization, verification, deployment artifacts).

Validate deployment files (no cloud provisioning):

```powershell
python scripts/validate_deployment_artifacts.py
docker compose -f docker-compose.prod.example.yml config
```

---

## Demo Limitations

- Executors return **mock/sandbox** results — not live email, payments, or GitHub issues unless a connector is explicitly enabled
- Demo mode allows unauthenticated **read** endpoints for the local UI; production deployments should restrict reads at the edge or via auth
- `security@openworld.dev` in [SECURITY.md](SECURITY.md) is a placeholder until a real disclosure mailbox exists
- No public hosted instance, custom domain, or real customers are claimed for v0.1.0

---

## Deployment Overview

Deployment artifacts exist (`docker/Dockerfile.api`, `docker/Dockerfile.web`, `docker-compose.prod.example.yml`) and are validated by tests.

**Status: READY FOR DEPLOYMENT — not ACTUALLY DEPLOYED.** You supply PostgreSQL, TLS, and secrets. A Render blueprint (`render.yaml`) is included for reference; **Hosted Preview remains not yet deployed** until you verify a live deployment. See [docs/deployment.md](docs/deployment.md).

Billing architecture is **BILLING-READY — not PAYMENTS-LIVE** ([docs/monetization.md](docs/monetization.md)).

---

## Documentation

- [Developer Onboarding](docs/onboarding.md)
- [Architecture](docs/architecture.md)
- [API Gateway](docs/gateway.md)
- [Policy Engine](docs/policy-engine.md)
- [Trust Model](docs/trust-model.md)
- [API Reference](docs/api.md)
- [SDK Guide](docs/sdk.md)
- [Development](docs/development.md)
- [Deployment](docs/deployment.md)
- [External beta checklist](docs/beta.md) (BETA-READY, not beta-live)
- [Roadmap](docs/roadmap.md)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT License — see [LICENSE](LICENSE).

---

**Human Intent. Machine Execution. Verifiable Results.**
