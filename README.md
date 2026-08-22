# OPENWORLD

## The Trust Layer for the Agentic Internet

> **Human Intent. Machine Execution. Verifiable Results.**

**OpenWorld Gateway v0.1.0 — Early Developer Preview**
**Release:** [OpenWorld Gateway v0.1.0](https://github.com/veerendrakalyanbabu-VKB/openworld/releases/tag/v0.1.0)
**Hosted Preview:** Not yet deployed

**Core principle: Never trust the agent. Verify the action.**

| | |
|---|---|
| [Documentation](docs/onboarding.md) | [Quick Start](#local-quickstart) |
| [SDK](docs/sdk.md) | [Architecture](docs/architecture.md) |
| [Security](SECURITY.md) | [Deployment](docs/deployment.md) |
| [Roadmap](docs/roadmap.md) | [Contributing](CONTRIBUTING.md) |

---

## What is OpenWorld?

OpenWorld is an open, developer-first **agent trust and execution layer**. AI agents propose actions; OpenWorld enforces **identity**, **capabilities**, **policy**, **risk**, **approval**, **execution**, **verification**, and **audit** before anything is trusted.

| Resource | Status |
|----------|--------|
| **GitHub source** | Public — [github.com/veerendrakalyanbabu-VKB/openworld](https://github.com/veerendrakalyanbabu-VKB/openworld) |
| **v0.1.0 release** | Available — [releases/tag/v0.1.0](https://github.com/veerendrakalyanbabu-VKB/openworld/releases/tag/v0.1.0) |
| **Local development** | Supported (see [Local Quickstart](#local-quickstart)) |
| **Hosted application** | **Not yet deployed** — no public URL exists |
| **Sandbox executors** | Demo/mock only — labeled **DEMO DATA**, not production integrations |

This is an **Early Developer Preview**. It is **not** enterprise production-ready, **not** a live cloud deployment, and **not** backed by real customer integrations.

---

## Trust Pipeline

Every action passes through a deterministic trust pipeline. The policy engine — not an LLM — decides authorization.

```
REQUESTED → IDENTITY → CAPABILITY → POLICY → RISK → DECISION → APPROVAL → EXECUTION → VERIFICATION → AUDIT
```

| Stage | What it enforces |
|-------|------------------|
| **Identity** | Bearer JWT maps to a registered agent |
| **Capabilities** | Explicit catalog grant (wildcards rejected) |
| **Policy** | Deterministic allow/deny rules |
| **Risk** | Explainable factors (recipient, sensitivity, financial impact) |
| **Decision** | Pipeline outcome before execution |
| **Approval** | Human gate when required |
| **Execution** | Registered executors only; direct bypass rejected |
| **Verification** | `EXECUTED` ≠ `VERIFIED` |
| **Audit** | Immutable lifecycle record |

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

Repository layout: `apps/` · `core/` · `packages/sdk/` · `openworld/` · `examples/` · `docs/` · `tests/` · `render.yaml`

---

## Local Quickstart

Full walkthrough: [Developer Onboarding](docs/onboarding.md) · [Gateway](docs/gateway.md) · [SDK](docs/sdk.md)

**Prerequisites:** Python 3.11+ · Node.js 20+ · PostgreSQL 17 recommended (SQLite OK for first boot)

> **LOCAL DEVELOPMENT ONLY** — URLs below work only while the local API and web processes are running on your machine.

### 1. Install

**PowerShell**

```powershell
python -m pip install -e ".[dev]"
```

**Linux / macOS**

```bash
python -m pip install -e ".[dev]"
```

### 2. Configure

**PowerShell:** `Copy-Item .env.example .env`
**Linux / macOS:** `cp .env.example .env`

### 3. Database migration

```bash
python -m alembic upgrade head
```

### 4. Start API

```powershell
python -m uvicorn apps.api.main:app --port 8000
```

**LOCAL DEVELOPMENT ONLY** (not publicly hosted):

| Endpoint | URL |
|----------|-----|
| API docs | `http://localhost:8000/api/docs` |
| Health | `http://localhost:8000/api/v1/health` |
| Readiness | `http://localhost:8000/api/v1/ready` |

### 5. Start web UI

```powershell
cd apps\web
npm install
npm run dev
```

**LOCAL DEVELOPMENT ONLY:** `http://localhost:3000`

### 6. Run Gateway quickstart

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
```

Restart the API after pulling code changes — a stale process can serve old pipeline behavior.

### Docker (local stack)

```bash
docker compose up
```

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

Lower-level client — see [SDK Guide](docs/sdk.md) and `examples/basic_action.py`:

```python
from packages.sdk.openworld import OpenWorldClient

# LOCAL DEVELOPMENT ONLY — API must be running on your machine
with OpenWorldClient(base_url="http://localhost:8000") as client:
    client.authenticate("agent-email-bot")
    result = client.actions.submit(
        agent="EmailBot",
        action="email.send",
        auto_approve=True,
        idempotency_key="readme-example-1",
    )
    print(result.action["status"])
```

---

## What's in v0.1.0

**Implemented:** Full trust pipeline · FastAPI gateway · Next.js UI · `AgentGateway` SDK · demo/sandbox executors · PostgreSQL/SQLite · Render blueprint (`render.yaml`)

**Simulated / demo only:** Email, payment, webhook executors · demo JWT issuance

**Planned — not in this release:** Hosted cloud deployment · external beta · live payments · enterprise SSO

See [Roadmap](docs/roadmap.md).

---

## Security

- Default deny in production · server-side authorization · execution bypass protection · immutable audit
- Secrets via environment variables only

See [SECURITY.md](SECURITY.md) and [Deployment](docs/deployment.md).

---

## Testing

```powershell
python -m pytest tests/ -q
python -m ruff check .
python scripts/validate_doc_links.py
cd apps\web
npm run lint
npm run build
```

Current suite: **197 tests passing**.

---

## Deployment

**Status: READY FOR DEPLOYMENT — not ACTUALLY DEPLOYED.**

A Render blueprint (`render.yaml`) is on `main` for reference. **Hosted Preview: Not yet deployed.** See [docs/deployment.md](docs/deployment.md).

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

See [CONTRIBUTING.md](CONTRIBUTING.md). Report security issues per [SECURITY.md](SECURITY.md) (placeholder contact documented there).

## License

MIT License — see [LICENSE](LICENSE).

---

**Human Intent. Machine Execution. Verifiable Results.**
