"""SQLAlchemy ORM models — persistence only, not domain logic."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from core.db.base import Base
from core.utils.time import utc_now


class AgentRow(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(255), default="system")
    status: Mapped[str] = mapped_column(String(32), default="active")
    capabilities: Mapped[list] = mapped_column(JSON, default=list)
    trust_dimensions: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class PolicyRow(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    rules: Mapped[list] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class PolicyVersionRow(Base):
    __tablename__ = "policy_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    policy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    rules: Mapped[list] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    change_action: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class ActionRow(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(255), default="")
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    target: Mapped[str] = mapped_column(String(512), default="")
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    requested_permissions: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="requested", index=True)
    policy_decision: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    stages: Mapped[list] = mapped_column(JSON, default=list)
    correlation_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    execution_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    verification_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    approval_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    approval_actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approval_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approval_decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(255), default="")
    decision: Mapped[str] = mapped_column(String(64), default="")
    policy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    correlation_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)


class IdempotencyRow(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("agent_id", "idempotency_key", name="uq_agent_idempotency_key"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    action_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    response_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status_code: Mapped[int] = mapped_column(Integer, default=200)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class BillingAccountRow(Base):
    __tablename__ = "billing_accounts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    entitlements: Mapped[dict] = mapped_column(JSON, default=dict)
    subscription_status: Mapped[str] = mapped_column(String(32), default="none")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class UsageCounterRow(Base):
    __tablename__ = "usage_counters"
    __table_args__ = (UniqueConstraint("account_id", "metric", "period_key", name="uq_usage_period"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    period_key: Mapped[str] = mapped_column(String(16), nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class UsageDedupRow(Base):
    __tablename__ = "usage_dedup"
    __table_args__ = (UniqueConstraint("account_id", "source_id", name="uq_usage_source"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
