"""Commercial limits. Does not evaluate identity, policy, risk, or approval."""

from __future__ import annotations

from dataclasses import dataclass

from core.billing.catalog import (
    DEFAULT_ACCOUNT_ID,
    DEFAULT_PLAN_ID,
    Entitlements,
    entitlements_for,
)
from core.billing.provider import BillingProvider, NoopBillingProvider
from core.db.billing_repositories import BillingAccountRepository, UsageRepository
from core.db.models import BillingAccountRow
from core.db.session import session_scope
from core.utils.time import utc_now


@dataclass
class QuotaDecision:
    allowed: bool
    reason: str = ""
    used: int = 0
    limit: int = 0


class BillingService:
    def __init__(self, provider: BillingProvider | None = None):
        self.provider = provider or NoopBillingProvider()

    def ensure_default_account(self) -> BillingAccountRow:
        with session_scope() as session:
            repo = BillingAccountRepository(session)
            existing = repo.get(DEFAULT_ACCOUNT_ID)
            if existing:
                return existing
            ents = entitlements_for(DEFAULT_PLAN_ID)
            row = BillingAccountRow(
                id=DEFAULT_ACCOUNT_ID,
                name="Default account",
                plan_id=DEFAULT_PLAN_ID,
                entitlements=ents.as_dict(),
                subscription_status="none",
            )
            return repo.save(row)

    def snapshot(self) -> dict:
        self.ensure_default_account()
        with session_scope() as session:
            account = BillingAccountRepository(session).get(DEFAULT_ACCOUNT_ID)
            assert account is not None
            period = utc_now().strftime("%Y-%m")
            used = UsageRepository(session).get_count(account.id, "actions", period)
            return {
                "account_id": account.id,
                "name": account.name,
                "plan_id": account.plan_id,
                "entitlements": account.entitlements,
                "subscription_status": account.subscription_status,
                "usage": {"metric": "actions", "period": period, "count": used},
                "billing_live": False,
                "payments": "BILLING-READY",
            }

    def set_plan(self, plan_id: str, *, actor_id: str) -> dict:
        ents = entitlements_for(plan_id)
        with session_scope() as session:
            repo = BillingAccountRepository(session)
            account = repo.get(DEFAULT_ACCOUNT_ID)
            if account is None:
                account = BillingAccountRow(
                    id=DEFAULT_ACCOUNT_ID,
                    name="Default account",
                    plan_id=plan_id,
                    entitlements=ents.as_dict(),
                    subscription_status="none",
                )
            else:
                account.plan_id = plan_id
                account.entitlements = ents.as_dict()
            repo.save(account)
        return {"plan_id": plan_id, "entitlements": ents.as_dict(), "actor_id": actor_id}

    def check_action_quota(self) -> QuotaDecision:
        self.ensure_default_account()
        with session_scope() as session:
            account = BillingAccountRepository(session).get(DEFAULT_ACCOUNT_ID)
            assert account is not None
            ents = Entitlements(**account.entitlements)
            period = utc_now().strftime("%Y-%m")
            used = UsageRepository(session).get_count(account.id, "actions", period)
            if used >= ents.max_actions_per_month:
                return QuotaDecision(
                    False,
                    "Monthly action entitlement exceeded",
                    used=used,
                    limit=ents.max_actions_per_month,
                )
            return QuotaDecision(True, used=used, limit=ents.max_actions_per_month)

    def record_action(self, source_id: str) -> None:
        self.ensure_default_account()
        with session_scope() as session:
            usage = UsageRepository(session)
            if not usage.try_reserve_source(DEFAULT_ACCOUNT_ID, source_id, "actions"):
                return
            period = utc_now().strftime("%Y-%m")
            usage.increment(DEFAULT_ACCOUNT_ID, "actions", period)
