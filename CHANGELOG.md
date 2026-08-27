# OpenWorld Gateway MVP v0.1.0

**Release:** [v0.1.0 on GitHub](https://github.com/veerendrakalyanbabu-VKB/openworld/releases/tag/v0.1.0) · **Hosted Preview:** Not yet deployed

## Added
- Complete trust pipeline: identity → capability → policy → risk → decision → approval → execution → verification → audit
- Deterministic policy engine with agent/action/condition matching
- Rule-based risk evaluation with explainable factors (recipient, data sensitivity, financial impact)
- Execution engine that **rejects direct bypass** (`pipeline_authorized` required)
- Registered sandbox executors (email, webhook, API, payment, invoice, optional GitHub)
- Distinct `EXECUTED` vs `VERIFIED` vs `VERIFICATION_FAILED` statuses
- Human approval workflow with approve/deny recorded in audit
- FastAPI gateway with JWT roles (`viewer`, `agent`, `operator`, `policy_admin`, `system_admin`)
- Agent create/update with explicit capability catalog (wildcards rejected)
- Next.js command center UI with action-detail pipeline view
- Python SDK `AgentGateway` (`from openworld import AgentGateway`) and CLI
- Demo mode with synthetic data, clearly labeled
- PostgreSQL/SQLite persistence, Alembic migrations, Docker, CI

## Security
- Server-side authorization on mutations
- No arbitrary shell, code, or SQL execution
- Security headers on API responses
- Secrets via environment variables only

## Known limitations
- Public demo executors are sandbox/mock unless a connector is explicitly enabled
- Demo JWT issuance is demo-mode only
- Cloud hosting, custom domain, and live payments are **not** included in this tag
