# Security Policy

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in OpenWorld, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

### How to Report

Email security concerns to: **security@openworld.dev** *(placeholder — not a live mailbox; configure before production use)*

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 5 business days
- **Resolution target**: Within 30 days for confirmed vulnerabilities

### Scope

In scope:
- OpenWorld API and core engines
- Authentication and authorization bypasses
- Policy engine circumvention
- Capability or execution boundary bypass
- Audit log tampering
- Arbitrary code execution via executors

Out of scope:
- Social engineering
- Denial of service via excessive requests
- Issues in third-party dependencies (report upstream)

### Safe Harbor

We will not pursue legal action against researchers who:
- Make a good faith effort to avoid privacy violations and data destruction
- Report vulnerabilities promptly
- Allow reasonable time for remediation before disclosure

---

## Security Model (v0.1.0)

OpenWorld Gateway v0.1.0 is an **Early Developer Preview**. The controls below are implemented in code and covered by automated tests; they do **not** constitute a formal security certification or enterprise guarantee.

### Default deny

- **Production / staging** (`OPENWORLD_DEMO_MODE=false`): unmatched policies **deny** by default (`policy_default_deny=true`).
- **Demo mode** (`OPENWORLD_DEMO_MODE=true`): default-allow is used only for local simulation with labeled synthetic data. Demo mode must not be used as production.

Startup validation (`validate_production_safety`) rejects staging/production when demo mode, SQLite, or the default dev secret is configured.

### Authorization

- Mutations (action submission, approvals, policy changes, role admin, agent create/update) require a valid JWT and appropriate role.
- Roles are resolved from stored agent metadata — never from an untrusted request body field.
- Demo JWT issuance endpoints are available **only in demo mode**.

### Capabilities

- Agents may only be granted **explicit catalog capabilities** (e.g. `email.send`).
- Unrestricted wildcard capabilities (`*`, `*.*`) are rejected on agent create/update and in the permission validator.
- Action aliases (e.g. `send_email`) are canonicalized at the API boundary before capability checks.

### Policy enforcement

- The deterministic policy engine evaluates agent, action, and conditions.
- LLMs do not authorize actions; they may recommend, but policy decides.

### Execution boundary

- `ExecutionEngine.execute()` requires `pipeline_authorized=True`.
- Direct calls without passing identity, capability, policy, and risk gates raise `ExecutionBypassError`.
- Only **registered executors** run actions — no arbitrary shell, SQL, or code execution paths.

### Verification

- Execution success (`EXECUTED`) is distinct from trust (`VERIFIED`).
- Failed verification produces `VERIFICATION_FAILED` — not silent success.

### Audit

- Lifecycle events (request, policy, risk, approval, execution, verification, blocks) are appended to the audit log with correlation IDs and enriched context.
- Audit export is bounded and requires authorization.

### Demo mode

- Sandbox executors return mock results labeled **DEMO DATA**.
- Demo telemetry and synthetic agents/policies are clearly identified in API responses (`demo_mode: true`).
- Connectors (e.g. GitHub issue create) are disabled by default and require explicit environment enablement.

### Production limitations (v0.1.0)

- Unauthenticated **read** endpoints remain open for the local demo UI; restrict reads in production deployments.
- CORS defaults to localhost origins — configure `OPENWORLD_CORS_ORIGINS` for your deployment.
- No hosted public instance or managed security operations are included in this release.

### Secret management

- No secrets in source code.
- Configure via environment variables (`OPENWORLD_SECRET_KEY`, `OPENWORLD_DATABASE_URL`, etc.).
- Default dev secret (`dev-only-not-for-production-use-32b-minimum-key`) is rejected in staging/production startup.

---

## Security Practices

- Environment variables for configuration
- Deterministic policy engine (not LLM-based authorization)
- Explicit executor registration (no arbitrary shell execution)
- Immutable audit logging
- Input validation on API endpoints
- API security headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Cache-Control`, `Content-Security-Policy`

---

## Dependency notes (2026-08-21)

Not force-upgraded for v0.1.0:

- Host `pip` may report advisories — upgrade the local pip tool separately
- Next.js 15 pulls transitive `postcss` and `sharp` advisories; `npm audit fix --force` would jump to Next 16 (breaking). Track an intentional Next upgrade separately.

---

**Navigation:** [README](README.md) · [Onboarding](docs/onboarding.md) · [SDK Guide](docs/sdk.md) · [Deployment](docs/deployment.md) · [Roadmap](docs/roadmap.md)
