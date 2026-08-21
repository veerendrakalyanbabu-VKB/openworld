"""Billing providers — no card data, no live charges in this milestone."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BillingProvider(ABC):
    """Future payment adapter. Must never grant Trust Core roles."""

    live: bool = False

    @abstractmethod
    def create_customer(self, account_id: str, email: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def create_subscription(self, account_id: str, plan_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def cancel_subscription(self, account_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_subscription(self, account_id: str) -> dict[str, Any]:
        raise NotImplementedError


class NoopBillingProvider(BillingProvider):
    """NON-PRODUCTION. Does not charge anyone. Does not report payment success."""

    live = False

    def create_customer(self, account_id: str, email: str) -> dict[str, Any]:
        return {
            "status": "not_configured",
            "live": False,
            "account_id": account_id,
            "message": "No payment provider is configured.",
        }

    def create_subscription(self, account_id: str, plan_id: str) -> dict[str, Any]:
        return {
            "status": "not_configured",
            "live": False,
            "plan_id": plan_id,
            "message": "Subscription checkout is not available.",
        }

    def cancel_subscription(self, account_id: str) -> dict[str, Any]:
        return {"status": "not_configured", "live": False, "account_id": account_id}

    def get_subscription(self, account_id: str) -> dict[str, Any]:
        return {"status": "none", "live": False, "account_id": account_id}


class MockBillingProvider(BillingProvider):
    """Test double. Explicitly non-production. Never reports a live charge."""

    live = False

    def create_customer(self, account_id: str, email: str) -> dict[str, Any]:
        return {"status": "mock", "live": False, "account_id": account_id}

    def create_subscription(self, account_id: str, plan_id: str) -> dict[str, Any]:
        return {"status": "mock", "live": False, "plan_id": plan_id, "charged": False}

    def cancel_subscription(self, account_id: str) -> dict[str, Any]:
        return {"status": "mock", "live": False, "account_id": account_id}

    def get_subscription(self, account_id: str) -> dict[str, Any]:
        return {"status": "mock", "live": False, "account_id": account_id}
