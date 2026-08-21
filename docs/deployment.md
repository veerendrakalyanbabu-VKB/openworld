# Cloud / production deployment

**Status: READY FOR DEPLOYMENT — not ACTUALLY DEPLOYED.**

This repository does not provision cloud accounts, managed databases, or TLS certificates.

## Architecture

```
Browser (HTTPS at your reverse proxy)
    → Frontend (Next.js)
    → API / Gateway (FastAPI, /api/v1)
    → Managed PostgreSQL (production) or local PostgreSQL (lab)
```

Keep it a modular monolith. Do not add microservices for this milestone.

Secrets live in the host environment or a secret manager. They are never baked into images.

## Environments

| Name | `OPENWORLD_ENVIRONMENT` | `OPENWORLD_DEMO_MODE` | Database |
|------|-------------------------|------------------------|----------|
| Local | `local` | true OK | SQLite or PostgreSQL |
| Demo | `demo` | true | labeled synthetic data |
| Staging | `staging` | **false** | PostgreSQL |
| Production | `production` | **false** | PostgreSQL |

Staging and production fail startup if demo mode, SQLite, or the default JWT secret is used.

## Migrations

`alembic upgrade head` is additive. API startup also applies head. Do not run `drop` or destructive schema commands against production.

```powershell
$env:OPENWORLD_DATABASE_URL="postgresql://..."
python -m alembic upgrade head
```

## Containers

- `docker/Dockerfile.api` — non-root, no reload, health on `/api/v1/health`
- `docker/Dockerfile.web` — `npm ci` + `npm start`
- `docker-compose.yml` — **local/demo** stack including PostgreSQL
- `docker-compose.prod.example.yml` — API + web only; you supply PostgreSQL

Validate locally (no cloud required):

```powershell
python scripts/validate_deployment_artifacts.py
docker compose -f docker-compose.prod.example.yml config
```

`config` only renders the file. It does not start billable resources.

## HTTPS

Terminate TLS at a reverse proxy (Caddy, nginx, or your cloud load balancer). The API is HTTP inside the private network.

## Health

- Liveness: `GET /api/v1/health`
- Readiness: `GET /api/v1/ready` (database ping)
- Logs: structlog with `request_id`

## Cost

Potentially billable if you create them yourself: VM/container hosting, managed PostgreSQL, load balancer, TLS certificates, egress. This repo does not enable those automatically.

## Rollback

Keep the previous image digest. Restore PostgreSQL from a backup taken before a migration. Do not replay demo seed onto production data.
