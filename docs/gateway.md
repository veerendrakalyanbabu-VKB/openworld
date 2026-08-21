# API Gateway

The gateway (`apps/api/gateway/`) is the HTTP edge in front of FastAPI routers. It does **not** run Trust Core.

## Purpose

Stabilize the developer-facing API:

- versioned paths (`/api/v1/`)
- correlation (`X-Request-ID`)
- structured errors
- request/response size bounds
- optional rate-limit hook (default NoOp)
- health and readiness

Authentication and authorization stay on routers. Policy, risk, approval, execution, and verification stay in `core/`.

## Request flow

```
Client / SDK
    → GatewayMiddleware (correlation, size, rate-limit hook, logs)
    → JWT / role dependencies (when required)
    → Router
    → Trust Core (for actions)
    → JSON response + X-Request-ID
```

## Failure modes

| HTTP | Meaning |
|------|---------|
| 401 | Missing or invalid bearer token |
| 403 | Authenticated but role/capability insufficient |
| 404 | Unknown resource or agent name in SDK lookup |
| 409 | Idempotency key reused with a different payload |
| 413 | Request body larger than `OPENWORLD_MAX_REQUEST_BYTES` |
| 429 | Rate limiter denied (only if a limiter is wired) |
| 503 | Readiness: database not connected |

Interactive OpenAPI: `http://localhost:8000/api/docs`.
