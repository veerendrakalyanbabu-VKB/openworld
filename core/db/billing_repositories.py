"""Billing repositories."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.db.models import BillingAccountRow, UsageCounterRow, UsageDedupRow
from core.utils.time import utc_now


class BillingAccountRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, account_id: str) -> BillingAccountRow | None:
        return self.session.get(BillingAccountRow, account_id)

    def save(self, row: BillingAccountRow) -> BillingAccountRow:
        existing = self.session.get(BillingAccountRow, row.id)
        if existing:
            existing.name = row.name
            existing.plan_id = row.plan_id
            existing.entitlements = row.entitlements
            existing.subscription_status = row.subscription_status
            existing.updated_at = utc_now()
            return existing
        self.session.add(row)
        return row


class UsageRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_count(self, account_id: str, metric: str, period_key: str) -> int:
        row = self.session.scalars(
            select(UsageCounterRow).where(
                UsageCounterRow.account_id == account_id,
                UsageCounterRow.metric == metric,
                UsageCounterRow.period_key == period_key,
            )
        ).first()
        return int(row.count) if row else 0

    def try_reserve_source(self, account_id: str, source_id: str, metric: str) -> bool:
        """Return True if this source_id is newly counted."""
        nested = self.session.begin_nested()
        try:
            self.session.add(
                UsageDedupRow(
                    id=str(uuid.uuid4()),
                    account_id=account_id,
                    source_id=source_id,
                    metric=metric,
                )
            )
            self.session.flush()
            nested.commit()
            return True
        except IntegrityError:
            nested.rollback()
            return False

    def increment(self, account_id: str, metric: str, period_key: str) -> int:
        row = self.session.scalars(
            select(UsageCounterRow).where(
                UsageCounterRow.account_id == account_id,
                UsageCounterRow.metric == metric,
                UsageCounterRow.period_key == period_key,
            )
        ).first()
        if row is None:
            row = UsageCounterRow(
                id=str(uuid.uuid4()),
                account_id=account_id,
                metric=metric,
                period_key=period_key,
                count=1,
            )
            self.session.add(row)
            return 1
        row.count = int(row.count) + 1
        row.updated_at = utc_now()
        return int(row.count)
