# Roadmap

## v0.1.0 — OpenWorld Gateway MVP (current public preview)

Implemented and covered by automated tests:

- [x] Trust pipeline (identity, capability, policy, risk, decision, approval, execution, verification, audit)
- [x] Deterministic policy + risk engines (not LLM authorization)
- [x] Direct execution bypass rejected
- [x] FastAPI gateway + Next.js command center
- [x] PostgreSQL/SQLite persistence and Alembic migrations
- [x] JWT authentication and server-side roles
- [x] Python SDK (`AgentGateway` / `OpenWorldClient`) + CLI
- [x] Demo/sandbox executors (labeled DEMO DATA)

Not claimed as live:

- [ ] Cloud deployment of a public instance
- [ ] Custom domain (`openworld.dev` or otherwise) — not verified as available
- [ ] External closed beta with real customers
- [ ] Live payment processing

## Next (developer product)

- [ ] Hosted preview environment
- [ ] Additional bounded connectors (SMTP, HTTP) behind explicit enablement
- [ ] Broader API docs and language SDKs

## Later (do not block MVP)

- Agent Passport / reputation / marketplace
- Enterprise SSO
- Private regional deployments
- Usage-based billing with a live payment provider (architecture is billing-ready, payments are not live)

See [monetization.md](monetization.md), [beta.md](beta.md), and [deployment.md](deployment.md).

---

**Navigation:** [README](../README.md) · [Onboarding](onboarding.md) · [SDK Guide](sdk.md) · [Deployment](deployment.md) · [Security](../SECURITY.md)
