"""Verification domain model."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from core.utils.time import utc_now


class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


class VerificationResult(BaseModel):
    """Result of action verification."""

    id: str
    action_id: str
    expected_result: str
    actual_result: str
    status: VerificationStatus = VerificationStatus.PENDING
    evidence: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    verified_at: datetime = Field(default_factory=utc_now)
