# Developer Onboarding

A new contributor should be able to run OpenWorld locally in one sitting. This page is the missing pieces around the [README](../README.md) quick start.

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 20+ |
| PostgreSQL | 17 (recommended) |
| pip | bundled with Python |

SQLite is enough for a first API boot. Use PostgreSQL before trusting persistence.

## Environment

```powershell
Copy-Item .env.example .env
```

```bash
cp .env.example .env
```

Never commit `.env`. Placeholders only live in `.env.example`.

## First action (under 10 minutes)

With the API running:

```powershell
python examples/gateway_quickstart.py
```

This submits a sandbox `send_email` through identity → capability → policy → risk → execution → verification → audit. It is DEMO DATA, not a live mailbox. Expected terminal output includes `policy=ALLOW`, `execution=sandbox (DEMO DATA)`, `verification=VERIFIED`, and `audit=recorded`.

## Commands (PowerShell)

From the repository root:

```powershell
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python -m uvicorn apps.api.main:app --port 8000
```

Another terminal:

```powershell
cd apps\web
npm install
npm run dev
```

Tests (API must be up for smoke):

```powershell
python -m pytest tests/ -q
python -m ruff check .
python scripts/smoke_test_api.py
cd apps\web
npm run lint
npm run build
```

SDK example (API on :8000, demo mode):

```powershell
python examples/basic_action.py
```

## Commands (Linux / macOS)

```bash
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python -m uvicorn apps.api.main:app --port 8000
```

```bash
cd apps/web && npm install && npm run dev
```

```bash
python -m pytest tests/ -q
python -m ruff check .
python scripts/smoke_test_api.py
python examples/basic_action.py
```

Schema also applies on API startup. `alembic upgrade head` is still the explicit developer check.

## First action

`examples/basic_action.py` authenticates as EmailBot, submits `email.send` (synthetic executor), prints status, then reads audit as OpsBot.

Identity is the JWT. The SDK does not decide policy.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| `401 Authentication required` | Call `authenticate(...)` or `set_token` before submit/approvals/audit |
| `403 Insufficient authorization` | Use OpsBot for approvals/audit, AdminBot for roles, ApiBot for policy writes |
| `409` on actions | Reused `Idempotency-Key` with a different body |
| `/ready` 503 | Database URL wrong or PostgreSQL not running |
| Frontend cannot reach API | `NEXT_PUBLIC_API_URL=http://localhost:8000` |
| `openworld` CLI not found | `pip install -e .` from repo root |
| GitHub connector "created" but `dry_run: true` | Live GitHub is **not** verified; enable only with env token/owner/repo |
| Alembic hangs at API startup | Another process holds the DB; stop extra uvicorn instances |

## What not to do

- Do not send `agent_id` in the action body and expect it to be trusted.
- Do not put secrets in frontend env except `NEXT_PUBLIC_API_URL`.
- Do not treat dry-run connector output as a live GitHub issue.
