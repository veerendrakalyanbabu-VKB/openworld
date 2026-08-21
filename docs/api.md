# API Reference

Base URL: `http://localhost:8000/api/v1`

Interactive docs: `http://localhost:8000/api/docs`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
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

- `X-Request-ID` — returned on all responses for tracing

## Error Format

```json
{
  "error": "Description",
  "message": "Actionable message",
  "request_id": "uuid"
}
```
