"""Commercial plan catalog — not Trust Core permissions."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Entitlements:
    max_agents: int
    max_actions_per_month: int
    max_connectors: int
    audit_retention_days: int
    team_members: int
    export_limit: int

    def as_dict(self) -> dict:
        return asdict(self)


PLAN_CATALOG: dict[str, Entitlements] = {
    "free": Entitlements(3, 100_000, 0, 7, 1, 100),
    "pro": Entitlements(25, 500_000, 1, 90, 5, 1_000),
    "team": Entitlements(100, 2_000_000, 3, 365, 25, 5_000),
    "enterprise": Entitlements(1_000, 10_000_000, 10, 3650, 500, 50_000),
}

DEFAULT_ACCOUNT_ID = "acct-default"
DEFAULT_PLAN_ID = "free"


def entitlements_for(plan_id: str) -> Entitlements:
    return PLAN_CATALOG[plan_id]


def public_catalog() -> list[dict]:
    return [
        {"plan_id": plan_id, "entitlements": ents.as_dict(), "pricing": None}
        for plan_id, ents in PLAN_CATALOG.items()
    ]
