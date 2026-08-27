# Cloud / production deployment

**Status: READY FOR DEPLOYMENT — not ACTUALLY DEPLOYED.**

This repository does not provision cloud accounts, managed databases, or TLS certificates. Applying `render.yaml` or following the steps below still requires manual action in your hosting provider.

## Architecture

```
Browser (HTTPS at your host / load balancer)
    → Next.js web service
    → FastAPI API (/api/v1)
    → Managed PostgreSQL
```

Keep it a modular monolith. Do not add microservices for this milestone.

Secrets live in the host environment or a secret manager. They are never baked into images or committed to git.

## Render (reference blueprint)

`render.yaml` describes two web services plus manual PostgreSQL setup:

| Service | Runtime | Build | Start |
|---------|---------|-------|-------|
| `openworld-api` | Python 3.12 | `pip install .` | `python -m uvicorn apps.api.main:app --host 0.0.0.0 --port $PORT` |
| `openworld-web` | Node 20 (`apps/web`) | `npm ci && npm run build` | `npm start` |

**Pre-deploy migration (API service):**

```bash
python -m alembic upgrade head
```

Configured in `render.yaml` as `preDeployCommand`. Migrations are additive only — do not run destructive schema commands against production.

**Health checks**

| Check | Path | Purpose |
|-------|------|---------|
| Liveness | `GET /api/v1/health` | Process up |
| Readiness | `GET /api/v1/ready` | Database connected |

Point Render's API health check at `/api/v1/health`. Use `/api/v1/ready` before routing traffic after deploy.

**Hosted preview:** Not yet deployed. After you create Render services, set `NEXT_PUBLIC_API_URL` to your API service URL and `OPENWORLD_CORS_ORIGINS` to your web service origin. Do not use `*` for CORS.

## Environments

| Name | `OPENWORLD_ENVIRONMENT` | `OPENWORLD_DEMO_MODE` | Database |
|------|-------------------------|------------------------|----------|
| Local | `local` | true OK | SQLite or PostgreSQL |
| Demo | `demo` | true | labeled synthetic data |
| Staging | `staging` | **false** | PostgreSQL |
| Production | `production` | **false** | PostgreSQL |

Staging and production fail startup if demo mode, SQLite, the default JWT secret, wildcard CORS, or localhost-only CORS defaults are used.

## Required production environment variables

| Variable | Purpose |
|----------|---------|
| `OPENWORLD_ENVIRONMENT` | `production` |
| `OPENWORLD_DEMO_MODE` | `false` |
| `OPENWORLD_POLICY_DEFAULT_DENY` | `true` |
| `OPENWORLD_SECRET_KEY` | ≥32 characters, non-default |
| `OPENWORLD_AUTH_BOOTSTRAP_TOKEN` | Separate secret used to obtain agent JWTs |
| `OPENWORLD_DATABASE_URL` | PostgreSQL connection string |
| `OPENWORLD_CORS_ORIGINS` | JSON array of allowed web origins (never `*`) |
| `NEXT_PUBLIC_API_URL` | Public API URL for the Next.js web service (not localhost in production) |

Render injects `PORT` for each web service. The API listens on `0.0.0.0` and uses Render's `PORT`. Local development continues to use port `8000` for the API and `3000` for the web UI when `PORT` is unset.

Example CORS value after you know the web origin:

```text
["https://your-web-service.onrender.com"]
```

## Migrations

`alembic upgrade head` is additive. API startup also applies head. Do not run `drop` or destructive schema commands against production.

```powershell
$env:OPENWORLD_DATABASE_URL="postgresql://..."
python -m alembic upgrade head
```

## Containers

- `docker/Dockerfile.api` — non-root, no reload, health on `/api/v1/health`, respects `PORT`
- `docker/Dockerfile.web` — `npm ci` + `npm start`
- `docker-compose.yml` — **local/demo** stack including PostgreSQL
- `docker-compose.prod.example.yml` — API + web only; you supply PostgreSQL
- `render.yaml` — Render blueprint (reference only; secrets marked `sync: false`)

Validate locally (no cloud required):

```powershell
python scripts/validate_deployment_artifacts.py
docker compose -f docker-compose.prod.example.yml config
```

`config` only renders the file. It does not start billable resources.

## HTTPS

Terminate TLS at Render (or your reverse proxy). The API is HTTP inside the private network between Render services unless you configure custom domains with TLS.

## Health

- Liveness: `GET /api/v1/health`
- Readiness: `GET /api/v1/ready` (database ping)
- Logs: structlog with `request_id`

## Production safety

Startup validation (`validate_production_safety`) rejects:

- `OPENWORLD_DEMO_MODE=true` in staging/production
- SQLite in staging/production
- Default dev JWT secret
- Wildcard (`*`) CORS
- Localhost-only CORS defaults when `OPENWORLD_ENVIRONMENT=production`

## Cost

Potentially billable if you create them yourself: VM/container hosting, managed PostgreSQL, load balancer, TLS certificates, egress. This repo does not enable those automatically.

## Rollback

Keep the previous image digest or Render deploy ID. Restore PostgreSQL from a backup taken before a migration. Do not replay demo seed onto production data.

---

**Navigation:** [README](../README.md) · [Onboarding](onboarding.md) · [SDK Guide](sdk.md) · [Security](../SECURITY.md) · [Roadmap](roadmap.md)
