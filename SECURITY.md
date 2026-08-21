# Security Policy

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in OpenWorld, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

### How to Report

Email security concerns to: **security@openworld.dev** (placeholder — update before production)

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

## Security Practices

- No secrets in source code
- Environment variables for configuration
- Deterministic policy engine (not LLM-based)
- Explicit executor registration (no arbitrary shell execution)
- Immutable audit logging
- Input validation on all API endpoints
