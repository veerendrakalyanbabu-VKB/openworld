# External beta

**Status: BETA-READY — not BETA-LIVE.**

No public launch. This is a controlled-lab checklist.

## Safety posture

| Control | Beta requirement |
|---------|------------------|
| Auth | JWT; demo token endpoints off when `OPENWORLD_DEMO_MODE=false` |
| Authorization | Roles from stored agent metadata, never request body |
| Policy | Default-deny in staging/production |
| Database | PostgreSQL 17 |
| Secrets | Non-default `OPENWORLD_SECRET_KEY` |
| Connectors | GitHub issue create disabled unless env-enabled; still through Trust Core |
| Audit | Append-only; export bounded (`limit ≤ 1000`) |
| Rate limit | `OPENWORLD_RATE_LIMIT_PER_MINUTE` (0 = off; in-process only) |
| Request bounds | `OPENWORLD_MAX_REQUEST_BYTES` / `OPENWORLD_MAX_RESPONSE_BYTES` |

Demo mode must not be used as beta. Set `OPENWORLD_ENVIRONMENT=staging` and `OPENWORLD_DEMO_MODE=false`.

## Tenant labeling — limitation

Header `X-OpenWorld-Tenant` is logged for correlation. **It does not isolate data.** Existing tables are single-tenant. Do not tell beta customers they are isolated from each other.

## Rate limiting

`MemoryRateLimiter` is per API process. Health/readiness are exempt. This is abuse damping, not a billing quota.

## Rollback

1. Stop the new API/web containers or processes.
2. Start the previous image/commit.
3. Restore PostgreSQL from the backup taken before the change if a migration ran.
4. Confirm `/api/v1/health` and `/api/v1/ready`.

## Incident handling

1. Disable connectors (`OPENWORLD_GITHUB_ENABLED=false`).
2. Rotate `OPENWORLD_SECRET_KEY` only with a planned token re-issue.
3. Preserve audit rows; do not delete them to "clean up" an incident.
4. Capture `X-Request-ID` from the reporter.

## Operator visibility

Operators use the command center plus `GET /api/v1/audit` and `/approvals`. Ordinary agents do not receive other agents' audit in production scoping.

## Checklist

- [ ] Staging env, demo mode off
- [ ] PostgreSQL backup tested
- [ ] JWT secret not default
- [ ] Default-deny confirmed
- [ ] Connector credentials not in git
- [ ] Rate limit set to a finite per-minute value
- [ ] Support contact and request-id instructions
- [ ] Rollback owner named
- [ ] No public DNS until this list is signed off
