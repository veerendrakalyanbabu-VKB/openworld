# Monetization foundation

**Status: BILLING-READY — not PAYMENTS-LIVE.**

No payment provider credentials are configured. Checkout returns `not_configured` and `live: false`. Card data is not stored.

## Tiers

`free`, `pro`, `team`, `enterprise` live in `core/billing/catalog.py`. Pricing is not hardcoded into Trust Core.

Entitlements (`max_agents`, `max_actions_per_month`, `max_connectors`, `audit_retention_days`, `team_members`, `export_limit`) are commercial limits. They do not grant roles, capabilities, or policy outcomes.

## Enforcement

Action quota is checked after JWT identity and **before** Trust Core execution. A denied quota is not an ALLOW from policy.

Plan changes: `POST /api/v1/billing/plan` as `SYSTEM_ADMIN` only. Request bodies cannot invent entitlements.

## Persistence

Tables: `billing_accounts`, `usage_counters`, `usage_dedup`. Duplicate `source_id` values are not counted twice.
