# API Reference

Base URL: `http://localhost:8000/api/v1`

Interactive docs: `http://localhost:8000/api/docs`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Liveness |
| GET | /ready | Readiness (database connectivity) |
| GET | /stats | System statistics |
| GET | /agents | List agents |
| GET | /agents/{id} | Get agent details |
| GET | /actions | List actions |
| POST | /actions | Create and process action |
| POST | /actions/simulate | Simulate policy evaluation |
| GET | /policies | List policies |
| POST | /policies | Create policy |
| GET | /approvals | List pending approvals |
| POST | /approvals/{id}/approve | Approve action |
| POST | /approvals/{id}/deny | Deny action |
| GET | /audit | List audit events |
| GET | /intelligence/query | Evidence-based queries |

## Headers

- `Authorization: Bearer <jwt>` — required for mutating and privileged reads
- `X-Request-ID` — correlation ID; echoed on every response (generated if omitted)
- `Idempotency-Key` — required for safe action retries (`POST /actions`)

## Error Format

```json
{
  "error": "unauthorized",
  "message": "Authentication required",
  "request_id": "uuid",
  "detail": "Authentication required"
}
```

`error` is a stable code (`unauthorized`, `forbidden`, `not_found`, `conflict`, `payload_too_large`, `rate_limit_exceeded`, …).
