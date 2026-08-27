"""Bounded connector interface — execution only after Trust Core gates."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from core.models.action import ActionRequest


class ConnectorError(Exception):
    """Base connector failure."""


class ConnectorValidationError(ConnectorError):
    """Input failed bounded schema validation."""


class ConnectorTimeoutError(ConnectorError):
    """External call exceeded timeout."""


@dataclass
class ConnectorResult:
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    live: bool = False
    dry_run: bool = False


class Connector(ABC):
    """One allowlisted external operation. Must not evaluate policy or identity."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def action(self) -> str:
        pass

    @abstractmethod
    async def run(self, action: ActionRequest) -> ConnectorResult:
        pass
